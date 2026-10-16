# Aura Studio — Mac Apple Silicon

Có hai gói cho **Mac Apple Silicon (M1 trở lên, gồm M3)**:

| Hệ điều hành | Gói tải |
| --- | --- |
| macOS 26 trở lên | [Aura-Studio-macOS26-Apple-Silicon.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-macOS26-Apple-Silicon.zip) |
| macOS 27 trở lên, runtime gốc | [Aura-Studio-macOS-Apple-Silicon.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-macOS-Apple-Silicon.zip) |

Gói macOS 26 dùng các binary media tương thích và thư viện llama/SRT được build bằng SDK 26.5, deployment target 26.0. Hai gói dùng cùng mã ứng dụng và cách nhập API key thủ công.

## Cài cho đồng nghiệp dùng Mac M3

Chọn đúng ZIP theo bảng trên tại [release private](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/tag/v0.1.8-aura-team.2), giải nén toàn bộ rồi chạy **Cai-dat-Aura-Studio.command**. App tự được chép vào `~/Applications/Aura Studio.app`; sau khi mở app, tự nhập key trong **Cài đặt → API Key**.

Không cần Python, Homebrew hay build từ source để chạy bản đóng gói. Giữ nguyên các file đi kèm gói cài. Có thể chạy qua Terminal tại thư mục giải nén:

```bash
bash Cai-dat-Aura-Studio.command
```

Khi tự lưu key trong app, cho phép thao tác Keychain nếu macOS hỏi. App dùng chữ ký ad hoc nội bộ; chưa có Developer ID/notarization. Nếu macOS yêu cầu cho phép mở lần đầu, thực hiện trong Cài đặt hệ thống.

## Model và dữ liệu

App kèm Python, Qt, FFmpeg, trình duyệt Douyin và engine CPU/OCR. Model weights tải riêng tại **Cài đặt → Gói tài nguyên**. Whisper dùng cho nhận dạng; HY-MT2/OmniVoice cần khi dùng dịch/giọng local. DeepSeek/ElevenLabs dùng API thay cho các model local tương ứng.

Dữ liệu ứng dụng ở `~/Library/Application Support/HaizFlow`; tên Keychain vẫn dùng HaizFlow để tương thích. Giọng và model ElevenLabs được chọn trong Cài đặt; mỗi người tự nhập key của mình. Gói cài không chứa hoặc tự nạp key. Credit/số dư tính trên tài khoản API bạn nhập.

Inference hiện dùng CPU; chưa có MPS/Metal cho Whisper/OmniVoice. Xuất H.264 ưu tiên VideoToolbox, có fallback CPU.

## Kiểm tra bản đóng gói

Bản Mac đã được kiểm tra mở giao diện Cocoa, engine CPU/OCR, Chromium, Keychain API và xuất video có cả hình/tiếng. Đường dịch DeepSeek và tạo giọng ElevenLabs được kiểm tra bằng HTTP giả lập, không gọi API tính phí. Kết quả này không khẳng định số dư, quyền giọng hoặc quota của tài khoản API.

Gói macOS 26 đã rà 1.340 binary arm64: không có mức tối thiểu cao hơn 26.0 và không có đường dẫn thư viện ngoài app (trừ thư viện hệ thống). Đã xuất H.264/AAC có phụ đề ASS và chạy self-test khi chặn đọc `/opt/homebrew`.

**Các thử nghiệm chạy trên Apple Silicon với macOS 27.2; chưa chạy trực tiếp trên macOS 26.** Chưa có bản Mac Intel.

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

## Build runtime tương thích macOS 26

Manifest ghim URL/SHA256 và ánh xạ thư viện ở `runtime/macos26-native-manifest.json`. Script riêng trong `scripts/macos26/` không sửa mã giao diện hoặc cơ chế nhập key.

1. Có sẵn app arm64 đã build bằng hướng dẫn trên hoặc giải nén gói Mac. Chuẩn bị Python có `requests`, `macholib`, CMake và Apple SDK 26.x.
2. Chạy `python scripts/macos26/fetch-bottles.py --cache /path/to/cache` để lấy runtime đã ghim (không cài Homebrew vào hệ thống).
3. Giải nén nguồn llama-cpp-python 0.3.34 và SRT 1.5.7 trong [Aura-Studio-macOS26-NativeSources.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-macOS26-NativeSources.zip), kiểm SHA theo manifest.
4. Build thư viện với SDK 26.x, sau đó lắp app mới:

```bash
bash scripts/macos26/build-native.sh /path/to/llama_cpp_python-0.3.34 /path/to/srt-1.5.7 /path/to/cache/kegs/openssl-3/openssl@3/3.6.4 /path/to/build /Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk
python scripts/macos26/assemble.py --base-app "/path/to/base/Aura Studio.app" --cache /path/to/cache --llama-build /path/to/build/llama --srt-build /path/to/build/srt --output "/path/to/new/Aura Studio.app"
python scripts/macos26/bundle-notices.py --cache /path/to/cache --app "/path/to/new/Aura Studio.app" --source-manifest /path/to/source-manifest.json --llama-source /path/to/llama_cpp_python-0.3.34
python scripts/macos26/audit.py "/path/to/new/Aura Studio.app" --report /path/to/audit.json
"/path/to/new/Aura Studio.app/Contents/MacOS/HaizFlow" --macos-self-test
```

Gói nguồn bổ sung kèm công thức, giấy phép, manifest, script và báo cáo kiểm tra. Dùng cùng [Aura-Studio-macOS-ThirdPartySources.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-macOS-ThirdPartySources.zip) cho các thành phần giữ nguyên; bảng nguồn cho biết file nào nằm trong gói nào.
