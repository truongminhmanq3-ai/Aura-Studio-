# Aura Studio — Mac Apple Silicon

## Cài cho đồng nghiệp dùng Mac M3

Tải **Aura-Studio-macOS-Apple-Silicon.zip** tại [release private](https://github.com/truongminhmanq3-ai/HaizFlow-macos-api/releases/tag/v0.1.8-aura-team.2), giải nén toàn bộ rồi chạy **Cai-dat-Aura-Studio.command**. App tự được chép vào `~/Applications/Aura Studio.app`; API DeepSeek/ElevenLabs hiện có được nạp vào Keychain.

Không cần Python, Homebrew hay build từ source để chạy bản đóng gói. Giữ các thư mục `team` và `scripts` đi kèm gói cài. Có thể chạy qua Terminal tại thư mục giải nén:

```bash
bash Cai-dat-Aura-Studio.command
```

Cho phép thao tác Keychain khi macOS hỏi. App dùng chữ ký ad hoc nội bộ; chưa có Developer ID/notarization. Nếu macOS yêu cầu cho phép mở lần đầu, thực hiện trong Cài đặt hệ thống.

## Model và dữ liệu

App kèm Python, Qt, FFmpeg, trình duyệt Douyin và engine CPU/OCR. Model weights tải riêng tại **Cài đặt → Gói tài nguyên**. Whisper dùng cho nhận dạng; HY-MT2/OmniVoice cần khi dùng dịch/giọng local. DeepSeek/ElevenLabs dùng API thay cho các model local tương ứng.

Dữ liệu ứng dụng ở `~/Library/Application Support/HaizFlow`; tên Keychain vẫn dùng HaizFlow để tương thích. Giọng và model ElevenLabs được chọn trong Cài đặt; cấu hình API không bị đổi. Credit/số dư dùng chung trên tài khoản team.

Inference hiện dùng CPU; chưa có MPS/Metal cho Whisper/OmniVoice. Xuất H.264 ưu tiên VideoToolbox, có fallback CPU.

## Kiểm tra bản đóng gói

Bản Mac đã được kiểm tra mở giao diện Cocoa, engine CPU/OCR, Chromium, Keychain API và xuất video có cả hình/tiếng. Đường dịch DeepSeek và tạo giọng ElevenLabs được kiểm tra bằng HTTP giả lập, không gọi API tính phí. Kết quả này không khẳng định số dư, quyền giọng hoặc quota của tài khoản API.

Đã kiểm tra trên máy Apple Silicon với macOS 27.2. Chưa xác nhận trên Mac Intel hoặc mọi phiên bản macOS khác.

## Build lại trên Mac

Cần CPython 3.13, Homebrew FFmpeg full và công cụ build native:

```bash
brew install python@3.13 ffmpeg-full cmake
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
CMAKE_ARGS='-DGGML_METAL=ON' .venv/bin/python -m pip install -r requirements-macos-build.txt
.venv/bin/python -m pip install --no-deps -e .
PLAYWRIGHT_BROWSERS_PATH="$PWD/runtime/playwright-browser" .venv/bin/python -m playwright install --no-shell chromium
.venv/bin/python scripts/build-macos.py --output "$PWD/dist-macos" --browser "$PWD/runtime/playwright-browser/chromium-1243"
```

Có thể tái sử dụng engine/browser đã kiểm chứng của một app Mac cùng kiến trúc:

```bash
.venv/bin/python scripts/build-macos.py --output "$PWD/dist-macos" --reuse-bundle "/path/to/Aura Studio.app"
```

Kiểm tra app vừa build:

```bash
PATH=/usr/bin:/bin "./dist-macos/Aura Studio.app/Contents/MacOS/HaizFlow" --macos-self-test
"./dist-macos/Aura Studio.app/Contents/MacOS/HaizFlow" --ui-smoke-test
open "./dist-macos/Aura Studio.app"
```

Xem [thư viện native và nguồn tương ứng](docs/macos-third-party.md). Giấy phép ứng dụng cũ đã gỡ; các điều khoản riêng của thư viện và model vẫn được giữ.
