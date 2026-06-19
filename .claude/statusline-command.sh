#!/usr/bin/env bash
# Claude Code status line
# Left:  dir [git branch]
# Right: session % | model | ctx X% (Yk/Zk tokens)

eval "$(python3 -c "
import sys, json
d = json.load(sys.stdin)
def g(*keys, default=''):
    v = d
    for k in keys:
        if isinstance(v, dict):
            v = v.get(k)
        else:
            return default
    return default if v is None else v
print(f'cwd={g(\"workspace\",\"current_dir\") or g(\"cwd\")!r}')
print(f'model={g(\"model\",\"display_name\")!r}')
pct = g('context_window','used_percentage', default='')
print(f'used_pct={pct!r}')
print(f'ctx_size={g(\"context_window\",\"context_window_size\", default=\"\")!r}')
print(f'input_tokens={g(\"context_window\",\"current_usage\",\"input_tokens\", default=\"\")!r}')
print(f'session_pct={g(\"rate_limits\",\"five_hour\",\"used_percentage\", default=\"\")!r}')
print(f'session_resets_at={g(\"rate_limits\",\"five_hour\",\"resets_at\", default=\"\")!r}')
")"

# Overlay volatile stats from hook-written live state if fresh (< 30s old)
_state="$HOME/.claude/statusline-live-state.json"
if [ -f "$_state" ]; then
  eval "$(python3 - <<'PYEOF'
import json, time, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/statusline-live-state.json')))
    if time.time() - d.get('_ts', 0) < 30:
        def g(src, *keys):
            v = src
            for k in keys:
                v = v.get(k) if isinstance(v, dict) else None
            return v
        fields = [
            ('used_pct',          'context_window', 'used_percentage'),
            ('ctx_size',          'context_window', 'context_window_size'),
            ('session_pct',       'rate_limits', 'five_hour', 'used_percentage'),
            ('session_resets_at', 'rate_limits', 'five_hour', 'resets_at'),
            ('model',             'model', 'display_name'),
        ]
        for var, *keys in fields:
            val = g(d, *keys)
            if val is not None:
                print(f'{var}={val!r}')
except Exception:
    pass
PYEOF
  2>/dev/null)"
fi

# Shorten home directory to ~
short_dir="${cwd/#$HOME/\~}"

# Git branch — skip optional locks
git_branch=""
if [ -n "$cwd" ] && git -C "$cwd" rev-parse --git-dir >/dev/null 2>&1; then
  git_branch=$(git -C "$cwd" -c gc.auto=0 symbolic-ref --short HEAD 2>/dev/null \
    || git -C "$cwd" -c gc.auto=0 rev-parse --short HEAD 2>/dev/null)
fi

# ANSI helpers
bold='\033[1m'
reset='\033[0m'
cyan='\033[1;36m'
yellow='\033[1;33m'
magenta='\033[0;35m'
white='\033[0;37m'
green='\033[0;32m'
orange='\033[0;33m'
red='\033[1;31m'
sep="${white}|${reset}"

# --- Left: path [branch] ---
left="$(printf "${cyan}${short_dir}${reset}")"
if [ -n "$git_branch" ]; then
  left+=" $(printf "${yellow} ${git_branch}${reset}")"
fi

# --- Right segments ---
parts=()

# Session % (5-hour rate limit)
if [ -n "$session_pct" ]; then
  s_int=$(printf '%.0f' "$session_pct")
  if [ "$s_int" -ge 80 ]; then s_col="$red"
  elif [ "$s_int" -ge 50 ]; then s_col="$orange"
  else s_col="$green"; fi
  reset_suffix=""
  if [ -n "$session_resets_at" ] && [ "$session_resets_at" -gt 0 ] 2>/dev/null; then
    reset_hm=$(date -d "@$session_resets_at" +%H:%M 2>/dev/null)
    [ -n "$reset_hm" ] && reset_suffix=" $(printf "${white}(→${reset_hm})${reset}")"
  fi
  parts+=("$(printf "${s_col}session:${s_int}%%${reset}")${reset_suffix}")
fi

# Model
if [ -n "$model" ]; then
  parts+=("$(printf "${magenta}${model}${reset}")")
fi

# Context: percentage + absolute tokens
if [ -n "$used_pct" ]; then
  used_int=$(printf '%.0f' "$used_pct")
  if [ "$used_int" -ge 80 ]; then ctx_col="$red"
  elif [ "$used_int" -ge 50 ]; then ctx_col="$orange"
  else ctx_col="$green"; fi

  ctx_str="$(printf "${ctx_col}ctx:${used_int}%%${reset}")"

  # Absolute token counts: derive used from percentage to stay consistent
  if [ -n "$ctx_size" ] && [ "$ctx_size" -gt 0 ]; then
    used_k=$(awk "BEGIN {printf \"%.0f\", ($used_pct / 100) * $ctx_size / 1000}")
    total_k=$(awk "BEGIN {printf \"%.0f\", $ctx_size / 1000}")
    ctx_str+=" $(printf "${white}(${used_k}k/${total_k}k)${reset}")"
  fi

  parts+=("$ctx_str")
fi

# Join right parts with separator
right=""
for part in "${parts[@]}"; do
  [ -n "$right" ] && right+=" $(printf "$sep") "
  right+="$part"
done

printf "%s  %s" "$left" "$right"
