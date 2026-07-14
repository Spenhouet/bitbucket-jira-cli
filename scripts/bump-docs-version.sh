#!/usr/bin/env bash
# Bump every version-pinning reference in README and the documentation tree.
#
# Patterns rewritten:
#   uvx.sh/bitbucket-jira-cli/<version>/install.sh
#   uvx.sh/bitbucket-jira-cli/<version>/install.ps1
#   bitbucket-jira-cli==<version>
#   spenhouet/bitbucket-jira-cli:<version>    (Docker pin; :latest left alone)
#
# Auto-discovers any file under README.md or docs/ that contains one of the
# patterns above, so no explicit file list needs maintaining as docs change.
#
# Usage: scripts/bump-docs-version.sh <new-version>
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <new-version>" >&2
  exit 1
fi
NEW="$1"

# Validate: tolerate "1.2.3", "1.2.3a4", "1.2.3rc1" etc. (anything pip accepts).
if [[ ! "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z]+)*$ ]]; then
  echo "error: '$NEW' does not look like a valid version" >&2
  exit 1
fi

PATTERN='(uvx\.sh/bitbucket-jira-cli/[^/[:space:]]+/install\.(sh|ps1)|bitbucket-jira-cli==[0-9]|spenhouet/bitbucket-jira-cli:[0-9])'

mapfile -t files < <(
  for root in README.md docs; do
    [[ -e "$root" ]] || continue
    if [[ -f "$root" ]]; then
      echo "$root"
    else
      find "$root" -type f \( -name '*.md' -o -name '*.mdx' \)
    fi
  done | xargs -r grep -lE "$PATTERN" 2>/dev/null
)

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No files contain version-pin patterns; nothing to update."
  exit 0
fi

for f in "${files[@]}"; do
  sed -i \
    -e "s|uvx\.sh/bitbucket-jira-cli/[^/[:space:]]*/install\.sh|uvx.sh/bitbucket-jira-cli/${NEW}/install.sh|g" \
    -e "s|uvx\.sh/bitbucket-jira-cli/[^/[:space:]]*/install\.ps1|uvx.sh/bitbucket-jira-cli/${NEW}/install.ps1|g" \
    -e "s|bitbucket-jira-cli==[0-9A-Za-z.\\-]*|bitbucket-jira-cli==${NEW}|g" \
    -e "s|spenhouet/bitbucket-jira-cli:[0-9][0-9A-Za-z.\\-]*|spenhouet/bitbucket-jira-cli:${NEW}|g" \
    "$f"
  echo "updated: $f"
done
