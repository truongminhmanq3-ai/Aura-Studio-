#!/bin/bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(cd -- "$script_dir/.." && pwd)
/usr/bin/osascript -l JavaScript "$script_dir/import-team-keys.js" "$repo_dir/team/team-api-keys.json"
