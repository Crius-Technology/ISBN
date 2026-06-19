"""Documentation sync to external docs repository.

Copies documentation files, adds auto-sync headers, and generates
Docusaurus sidebar category files.
"""

import json
import re
import shutil
import sys
from pathlib import Path

import config_loader


def rewrite_internal_links(content: str, docs_dir: str) -> str:
    """Rewrite markdown links that reference the docs directory to sibling-relative paths.

    After flattening, files from docs/ and root are siblings, so links like
    `[text](docs/file.md)` must become `[text](./file.md)`.
    """
    prefix = docs_dir.rstrip("/") + "/"
    # Match markdown links: [text](docs/path) — with optional anchor
    pattern = re.compile(r"(\[[^\]]*\]\()" + re.escape(prefix) + r"([^)]+\))")
    return pattern.sub(r"\1./\2", content)


def sync_docs(
        source_checkout: str, target_checkout: str
) -> tuple[bool, list[dict[str, str]]]:
    """Sync documentation from source to target repository.

    Args:
        source_checkout: Path to the source repository checkout
        target_checkout: Path to the target docs repository checkout

    Returns:
        Tuple of (changed, broken_links) where changed is True if changes
        were made, and broken_links is a list of broken link dicts.
    """
    project_name = config_loader.get_project_name()
    docs_dir = config_loader.get_docs_dir()
    sync_config = config_loader.get_doc_sync_config()

    target_base_path = sync_config.get("target_base_path", "")
    if not target_base_path:
        print("::error::doc_sync.target_base_path is required in .doc-config.yml")
        sys.exit(1)

    source_dir = Path(source_checkout) / docs_dir
    target_dir = Path(target_checkout) / target_base_path / project_name

    if not source_dir.exists():
        print(f"::error::Source directory {source_dir} does not exist")
        sys.exit(1)

    # Clean and recreate target directory
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy all docs (excluding files listed in sync_exclude)
    exclude = config_loader.get_sync_exclude()
    ignore = shutil.ignore_patterns(*exclude) if exclude else None
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True, ignore=ignore)

    # Copy root-level markdown files (auto-detected)
    source_root = Path(source_checkout)
    for md_file in source_root.glob("*.md"):
        if md_file.name in exclude:
            continue
        shutil.copy2(md_file, target_dir / md_file.name)

    # Rewrite internal links and add auto-sync header to markdown files
    notice = f"\n<!-- Auto-synced from {project_name}. Do not edit directly. -->"
    for md_file in target_dir.rglob("*.md"):
        content = md_file.read_text()
        modified = False

        # Rewrite docs/ prefix links to sibling-relative
        rewritten = rewrite_internal_links(content, docs_dir)
        if rewritten != content:
            content = rewritten
            modified = True

        # Inject auto-sync notice into frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = f"---{parts[1]}---{notice}{parts[2]}"
                modified = True

        if modified:
            md_file.write_text(content)

    # Generate _category_.json files
    sidebar_categories = sync_config.get("sidebar_categories", [])
    for category in sidebar_categories:
        cat_path = category.get("path", "")
        cat_dir = target_dir / cat_path if cat_path else target_dir
        cat_dir.mkdir(parents=True, exist_ok=True)

        cat_data = {"label": category.get("label", ""), "position": category.get("position", 1)}
        if "collapsible" in category:
            cat_data["collapsible"] = category["collapsible"]
        if "collapsed" in category:
            cat_data["collapsed"] = category["collapsed"]

        cat_file = cat_dir / "_category_.json"
        cat_file.write_text(json.dumps(cat_data, indent=2) + "\n")

    # Validate links in synced markdown files
    broken_links = validate_links(target_dir)
    if broken_links:
        # GitHub Actions annotations (shown inline on files)
        for bl in broken_links:
            rel = Path(bl["file"]).relative_to(target_dir)
            reason = bl.get("reason", "")
            print(f"::error file={rel}::Broken link [{bl['text']}]({bl['link']}): {reason}")

        # Human-readable summary in the log
        print(f"\n{'=' * 60}")
        print(f"BROKEN LINKS SUMMARY — {len(broken_links)} issue(s) found")
        print(f"{'=' * 60}")
        for i, bl in enumerate(broken_links, 1):
            rel = Path(bl["file"]).relative_to(target_dir)
            print(f"\n  {i}. [{bl['text']}]({bl['link']})")
            print(f"     File:   {rel}")
            print(f"     Reason: {bl.get('reason', 'Unknown')}")
        print(f"\n{'=' * 60}")
        print("Fix these links in the source repository before syncing again.\n")

        report_path = Path(target_checkout) / "broken_links_report.md"
        report_path.write_text(format_broken_links_report(broken_links, target_dir))
        print(f"Broken links report written to {report_path}")

    # Write autogenerated sidebar file if configured
    base_dir = Path(target_checkout) / target_base_path
    ensure_autogenerated_sidebar(sync_config, base_dir)

    # Ensure this project appears in the index page
    ensure_index_entry(base_dir, project_name)

    return True, broken_links


def validate_links(target_dir: Path) -> list[dict[str, str]]:
    """Scan markdown files for broken relative links.

    Returns a list of dicts with 'file', 'link', and 'text' keys for each broken link.
    """
    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    broken: list[dict[str, str]] = []

    for md_file in target_dir.rglob("*.md"):
        content = md_file.read_text()
        for match in link_pattern.finditer(content):
            text, target = match.group(1), match.group(2)

            # Skip absolute URLs, anchors, and absolute paths
            if target.startswith(("http://", "https://", "mailto:", "#", "/")):
                continue

            # Strip anchor suffix
            link_path = target.split("#")[0]
            if not link_path:
                continue

            resolved = (md_file.parent / link_path).resolve()
            if resolved.is_file():
                continue
            # Directory-style link (e.g. ./foo/ or ./foo) — needs index.md inside
            if resolved.is_dir() and (resolved / "index.md").exists():
                continue
            # Directory-style link where the target is actually a .md file
            # e.g., ../architecture/software-design/ -> ../architecture/software-design.md
            resolved_as_md = resolved.parent / f"{resolved.name}.md"
            if not resolved.exists() and resolved_as_md.is_file():
                continue

            if resolved.is_dir():
                reason = (
                    f"Directory '{link_path}' exists but has no index.md. "
                    "Docusaurus cannot serve a directory link without an index page. "
                    "Add an index.md to the directory or link to a specific file instead."
                )
            else:
                reason = f"Target '{link_path}' does not exist."

            broken.append({"file": str(md_file), "link": target, "text": text, "reason": reason})

    return broken


def format_broken_links_report(
        broken_links: list[dict[str, str]], target_dir: Path
) -> str:
    """Format broken links as a markdown report for PR body inclusion."""
    lines = [
        "## Broken Links Detected",
        "",
        "The following relative links point to files that do not exist in the synced output.",
        "**Action required:** fix these links in the source repository.",
        "",
        "| File | Link Text | Target | Reason |",
        "|------|-----------|--------|--------|",
    ]
    for bl in broken_links:
        rel = Path(bl["file"]).relative_to(target_dir)
        reason = bl.get("reason", "")
        lines.append(f"| `{rel}` | {bl['text']} | `{bl['link']}` | {reason} |")
    lines.append("")
    return "\n".join(lines)


def ensure_autogenerated_sidebar(sync_config: dict, docusaurus_dir: Path) -> None:
    """Write a Docusaurus sidebar file that uses autogenerated directory discovery.

    Only writes if `sidebar_file` is configured in doc_sync config. Idempotent.
    """
    sidebar_file = sync_config.get("sidebar_file")
    if not sidebar_file:
        return

    sidebar_path = docusaurus_dir / sidebar_file
    sidebar_content = """\
import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
    mySidebar: [
        {
            type: "autogenerated",
            dirName: "."
        }
    ]
};

export default sidebars;
"""
    sidebar_path.parent.mkdir(parents=True, exist_ok=True)
    sidebar_path.write_text(sidebar_content)
    print(f"Wrote sidebar file: {sidebar_path}")


def ensure_index_entry(base_dir: Path, project_name: str) -> None:
    """Ensure the project appears in the technology index page.

    Adds a bullet entry linking to the project's synced directory if not already present.
    """
    index_path = base_dir / "index.md"
    if not index_path.exists():
        return

    content = index_path.read_text()
    # Check if project is already listed
    if f"from the {project_name} repository" in content or f"({project_name}/" in content:
        return

    # Build a display name from the project slug
    display_name = project_name.replace("-", " ").title()

    entry = f"- **{display_name}** -- Technical documentation (synced automatically from the {project_name} repository)\n"

    # Append after the last bullet under ## Products, or at the end
    if "## Products" in content:
        # Find the last line that starts with "- " after ## Products
        lines = content.split("\n")
        in_products = False
        last_bullet = -1
        for i, line in enumerate(lines):
            if line.startswith("## Products"):
                in_products = True
            elif in_products and line.startswith("- "):
                last_bullet = i
            elif in_products and last_bullet >= 0 and line.startswith("##"):
                break
        if last_bullet >= 0:
            lines.insert(last_bullet + 1, entry.rstrip())
        else:
            # No bullets yet, add after the heading
            for i, line in enumerate(lines):
                if line.startswith("## Products"):
                    lines.insert(i + 1, "")
                    lines.insert(i + 2, entry.rstrip())
                    break
        content = "\n".join(lines)
    else:
        content = content.rstrip() + "\n\n## Products\n\n" + entry

    index_path.write_text(content)
    print(f"Added {project_name} to index: {index_path}")


def get_sync_metadata() -> dict[str, str]:
    """Get metadata for the sync PR."""
    project_name = config_loader.get_project_name()
    return {
        "branch_name": f"doc-sync/{project_name}",
        "pr_title": f"sync: update {project_name} documentation",
        "commit_message": (
            f"sync: update {project_name} documentation from source\n\n"
            f"Auto-synced from {project_name}/{config_loader.get_docs_dir()}/ on merge to develop."
        ),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python doc_sync.py <source_checkout> <target_checkout>")
        sys.exit(1)

    changed, broken_links = sync_docs(sys.argv[1], sys.argv[2])
    if changed:
        metadata = get_sync_metadata()
        print(f"BRANCH_NAME={metadata['branch_name']}")
        print(f"PR_TITLE={metadata['pr_title']}")
        print(f"COMMIT_MESSAGE={metadata['commit_message']}")
        if broken_links:
            print("BROKEN_LINKS=true")
