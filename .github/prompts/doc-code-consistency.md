# Documentation-Code Consistency Check

## Context
You are reviewing a pull request for documentation-code consistency.
The project documentation lives in `{docs_dir}/`.

## Changed files
{changed_files_list}

## Instructions
1. Use the `list_templates` MCP tool to see available documentation templates
2. For each changed documentation file:
   - Read the file and identify its `type` from frontmatter
   - Use `get_template` to fetch the matching template
   - Use `evaluate_doc` to check structural compliance
   - Explore the codebase to find related source code
   - Verify the documentation accurately reflects the code
3. For each changed code file:
   - Identify which documentation files reference or describe this code
   - Verify those docs are still accurate
4. Report findings as a structured JSON with severity levels

## Output
Write a markdown report to `.github/scripts/consistency_report.md` with the following format:

```markdown
## Documentation-Code Consistency Report

### [icon] `file_path`

- **[type]**: Description of finding
  - Suggestion for fix

---
[Overall summary]
```

Use these severity icons:
- OK: check mark
- Warning: warning sign
- Error: cross mark

Exit with a non-zero status if any errors are found.
