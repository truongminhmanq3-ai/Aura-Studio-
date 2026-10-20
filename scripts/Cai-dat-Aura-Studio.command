#!/bin/bash
set -euo pipefail
package_dir=$(cd -- "$(dirname -- "$0")" && pwd)
app_source="$package_dir/Aura Studio.app"

if [ "$(uname -s)" != Darwin ]; then
 echo 'Gói này dành cho macOS Apple Silicon.' >&2
 exit 1
fi
if [ "$(uname -m)" != arm64 ] && [ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || true)" != 1 ]; then
 echo 'Gói này cần Mac chip Apple Silicon (M1 trở lên).' >&2
 exit 1
fi
if [ ! -d "$app_source" ]; then
 echo 'Hãy giải nén toàn bộ gói Aura Studio trước, rồi chạy script trong thư mục vừa giải nén.' >&2
 exit 1
fi
/usr/bin/codesign --verify --deep --strict "$app_source"
if [ "${1:-}" = --verify-only ]; then
 echo 'Gói Aura Studio hợp lệ. Chưa cài app.'
 exit 0
fi
if [ "$#" -ne 0 ]; then
 echo 'Chạy: bash Cai-dat-Aura-Studio.command' >&2
 exit 1
fi
if /usr/bin/pgrep -x HaizFlow >/dev/null 2>&1; then
 echo 'Hãy thoát Aura Studio đang mở rồi chạy lại script cài đặt.' >&2
 exit 1
fi
install_root="$HOME/Applications"
mkdir -p "$install_root"
staging_root=$(mktemp -d "$install_root/.aura-install.XXXXXX")
cleanup() { rm -rf -- "$staging_root"; }
trap cleanup EXIT
/usr/bin/ditto "$app_source" "$staging_root/Aura Studio.app"
/usr/bin/codesign --verify --deep --strict "$staging_root/Aura Studio.app"
target_app="$install_root/Aura Studio.app"
if [ -e "$target_app" ]; then
 backup_app="$install_root/Aura Studio-backup-$(date +%Y%m%d-%H%M%S).app"
 mv "$target_app" "$backup_app"
 echo "Bản app trước được giữ tại: $backup_app"
fi
mv "$staging_root/Aura Studio.app" "$target_app"
echo "Đã cài Aura Studio tại: $target_app"
echo 'Mở Cài đặt → API Key để tự nhập key của bạn. Model local tải trong Cài đặt → Gói tài nguyên khi cần.'
/usr/bin/open "$target_app"
