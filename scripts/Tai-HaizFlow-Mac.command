#!/bin/bash
set -euo pipefail
repo='truongminhmanq3-ai/HaizFlow-macos-api'
tag='v0.1.8-aura-team.2'
if ! command -v gh >/dev/null 2>&1 || ! gh auth status --hostname github.com >/dev/null 2>&1; then
 echo 'Tải gói Aura Studio bằng trình duyệt tại:'
 echo "https://github.com/$repo/releases/tag/$tag"
 echo 'Đăng nhập GitHub bằng tài khoản có quyền repo, tải ZIP rồi giải nén và chạy Cai-dat-Aura-Studio.command.'
 exit 1
fi
case "${1:-app}" in
 app) package='Aura-Studio-macOS-Apple-Silicon.zip' ;;
 sources) package='Aura-Studio-macOS-ThirdPartySources.zip' ;;
 *) echo 'Dùng: bash scripts/Tai-HaizFlow-Mac.command [app|sources]' >&2; exit 1 ;;
esac
download_dir=$(mktemp -d "$PWD/Aura-Studio-download.XXXXXX")
gh release download "$tag" --repo "$repo" --pattern "$package" --pattern SHA256SUMS.txt --dir "$download_dir"
(cd "$download_dir" && /usr/bin/shasum -a 256 -c <(/usr/bin/awk -v filename="$package" '$2 == filename' SHA256SUMS.txt))
/usr/bin/ditto -x -k "$download_dir/$package" "$download_dir"
echo "Đã tải và giải nén tại: $download_dir"
/usr/bin/open "$download_dir"
