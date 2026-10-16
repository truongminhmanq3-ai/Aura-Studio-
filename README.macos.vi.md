# Aura Studio — hướng dẫn macOS và build

Aura Studio dành cho macOS Apple Silicon (arm64). Bản đã build và thử trên macOS 27.0; chưa kiểm chứng trên Intel hoặc các phiên bản macOS khác.

## Tạo app từ mã nguồn

Repo hiện chỉ cung cấp mã nguồn. Các release và tag cũ đã được gỡ; chưa có bản cài mới trên GitHub. Làm theo phần [Build lại trên Mac](#build-lại-trên-mac), rồi mở app vừa build.

Tên executable và đường dẫn build vẫn dùng `HaizFlow` để tương thích với cấu hình hiện có. Giao diện dùng tên Aura Studio. Nạp API dùng chung bằng `bash scripts/Nap-key-team-Mac.command` từ thư mục repo sau khi đóng app.

Dữ liệu được lưu tại `~/Library/Application Support/HaizFlow`, không ghi vào bên trong `.app`. API key được lưu trong macOS Keychain. Bản này chạy AI theo đường CPU; chưa có đường tăng tốc inference bằng MPS/Metal. Xuất H.264 ưu tiên VideoToolbox, có fallback CPU.

Model không nằm trong app. Vào **Cài đặt → Gói tài nguyên** và cài các gói cần dùng: Whisper Small, HY-MT2 CPU (hoặc dùng Gemini/DeepSeek), OmniVoice, Demucs và OCR tuỳ quy trình. Việc tải model cần mạng và dung lượng lưu trữ riêng. Đăng nhập/captcha Douyin vẫn do người dùng thao tác trong trình duyệt của app.

Bản macOS cập nhật thủ công bằng `.app` mới; không tải hoặc chạy bộ cài Windows từ upstream.

## Kiểm chứng

- Chạy kiểm thử QML/UI từ mã nguồn và từ bản đóng gói.
- Kiểm thử các bộ xử lý CPU/vision từ executable đóng gói.
- Mở Chromium headless với trang trống; không truy cập tài khoản Douyin.
- Xuất video mẫu có phụ đề tiếng Việt, watermark và âm thanh bằng pipeline render của HaizFlow; xác nhận đầu ra có cả video/audio.
- 44 kiểm thử về queue, resume, timing và ranh giới macOS đã qua.
- Đã nhận dạng và dịch một clip thực tế gồm 11 câu bằng DeepSeek. Bước ElevenLabs dừng ở HTTP 402 do giới hạn giọng/gói tài khoản; lần chạy đó chưa có video hoàn tất. Người dùng tự kiểm tra video và giọng của mình trong ứng dụng.
- Một số icon dùng glyph Segoe Fluent Icons của Windows chưa hiển thị đúng trên Mac; các nhãn chữ và nút vẫn dùng được.
- Decoder TorchCodec là thành phần tuỳ chọn và chưa hoạt động với FFmpeg 9; đường nhận dạng chính đọc âm thanh qua FFmpeg rồi truyền waveform vào WhisperX.

## Chọn OmniVoice hoặc ElevenLabs

OmniVoice được giữ nguyên làm lựa chọn mặc định, chạy local bằng CPU trên bản Mac. Cài gói OmniVoice trong **Cài đặt → Gói tài nguyên** trước khi sử dụng. Nhân bản giọng local và nhận diện nhiều người nói của OmniVoice vẫn giữ nguyên.

Để dùng ElevenLabs:

1. Vào **Cài đặt → API key → ElevenLabs**.
2. Dán API key, bấm **Lưu key và tải giọng**. Key lưu trong Keychain; app không ghi key vào dự án hay file cài đặt.
3. Chọn giọng từ tài khoản, hoặc dán **Voice ID**, rồi bấm **Lưu giọng và model**. Flash v2.5 là model mặc định có hỗ trợ tiếng Việt; có thêm lựa chọn Eleven v3.
4. Trong dự án, ở **Công cụ giọng đọc**, chọn **ElevenLabs · API**, rồi chọn giọng. Bạn có thể đổi lại **OmniVoice · CPU** tại cùng vị trí.
5. Chế độ tự động, hàng loạt và hộp thoại tạo giọng thủ công đều dùng lựa chọn này. Mỗi dự án lưu công cụ và giọng riêng; chỉnh model ElevenLabs trong Cài đặt áp dụng cho những lần tạo giọng sau đó.

ElevenLabs cần Internet và credit trên tài khoản. API key cần quyền Text to Speech; quyền Voices cần cho tải danh sách giọng. Các giọng đã nhân bản trong tài khoản ElevenLabs cũng có thể chọn; mẫu nhân bản local của OmniVoice không tự gửi lên ElevenLabs.

Ứng dụng báo riêng lỗi key/quyền truy cập/hết credit/lỗi mạng. Các đoạn MP3 đã hoàn tất có cache; khi tiếp tục, app chỉ tạo lại đoạn thiếu hoặc có nội dung/giọng/model thay đổi. App không tự gọi lại yêu cầu tạo giọng bị lỗi để tránh phát sinh nhiều lần tính credit.

Đã kiểm tra UI chọn qua lại hai công cụ, lưu/mở lại cấu hình dự án, API giả lập qua HTTP, nhận và giải mã MP3 bằng FFmpeg, cache, tiếp tục sau lỗi, hủy tác vụ và che thông tin key. **106 kiểm thử và 24 subtest qua**, gồm kiểm thử hồi quy OmniVoice. Đã kiểm tra đọc thông tin tài khoản và danh sách giọng qua ElevenLabs thật. Chưa xác nhận tạo giọng thành công với tài khoản hiện tại; một giọng Voice Library bị giới hạn API trên gói Free. Chưa chạy inference OmniVoice với model tải về.

Tích hợp dùng [API tạo giọng](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) và [API danh sách giọng](https://elevenlabs.io/docs/api-reference/voices/search). Tham khảo [các model ElevenLabs](https://elevenlabs.io/docs/overview/models).

## Dịch bằng DeepSeek

HY-MT2 và Gemini được giữ nguyên; DeepSeek được thêm thành hai lựa chọn **DeepSeek Flash · API** và **DeepSeek V4 Pro · API** trong **Model dịch**. Cả xử lý tự động, hàng loạt và công cụ dịch thủ công đều dùng được. Chọn DeepSeek không cần tải model HY-MT2.

1. Vào **Cài đặt → API key → DeepSeek**.
2. Dán key từ [DeepSeek Platform](https://platform.deepseek.com/api_keys), bấm **Lưu key**. Có thể để trống và dán sau; lưu key không gọi API dịch.
3. Trong dự án, chọn một model DeepSeek ở **Model dịch**, rồi chạy dịch/xử lý như bình thường.

Key chỉ được lưu trong Keychain, không ghi vào dự án hay file cài đặt. DeepSeek cần Internet và số dư API. App báo riêng lỗi thiếu key, key sai, quyền truy cập, hết số dư, giới hạn tốc độ và lỗi mạng. Khi chưa có key, app không chuyển sang model khác.

Bản dịch giữ nguyên số câu và mốc thời gian phụ đề. Mỗi batch hợp lệ được lưu để tiếp tục từ câu thiếu sau lỗi hoặc tạm dừng. Đổi model, ngôn ngữ hoặc nội dung sẽ tạo cache khác. Dữ liệu API thiếu câu, sai thứ tự, rỗng hoặc bị cắt được từ chối; bản dịch đã xuất trước đó được giữ nguyên. Yêu cầu API lỗi không tự gửi lại; bạn có thể chạy tiếp sau khi xử lý nguyên nhân.

Đã kiểm tra HTTP giả lập, Unicode, thứ tự câu, thời gian, lỗi API, che key, hủy tác vụ, tiếp tục sau lỗi và lựa chọn model trên UI. Bộ kiểm tra chọn lọc cho phần dịch, giọng đọc, dự án, gói tài nguyên và resume: **208 kiểm thử + 24 subtest qua**. Một kiểm thử shutdown từ upstream cần import WhisperX/Torch trực tiếp nên không chạy trong môi trường Core build nhẹ; engine AI được kiểm tra riêng từ app đóng gói. Đã gọi DeepSeek thật và dịch 11 câu trong một clip thử nghiệm.

Tích hợp theo [API chat completion](https://api-docs.deepseek.com/api/create-chat-completion/) và [danh sách model DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/).

## Build lại trên Mac

Chuẩn bị CPython 3.13, Homebrew `ffmpeg-full` và công cụ C/C++ nếu phải biên dịch llama.cpp:

```bash
brew install python@3.13 ffmpeg-full cmake
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
CMAKE_ARGS='-DGGML_METAL=ON' .venv/bin/python -m pip install -r requirements-macos-build.txt
.venv/bin/python -m pip install --no-deps -e .
PLAYWRIGHT_BROWSERS_PATH="$PWD/runtime/playwright-browser" .venv/bin/python -m playwright install --no-shell chromium
.venv/bin/python scripts/build-macos.py --output "$PWD/dist-macos" --browser "$PWD/runtime/playwright-browser/chromium-1243"
```

Chạy kiểm tra bản đóng gói với PATH tối giản:

```bash
PATH=/usr/bin:/bin ./dist-macos/HaizFlow.app/Contents/MacOS/HaizFlow --macos-self-test
./dist-macos/HaizFlow.app/Contents/MacOS/HaizFlow --ui-smoke-test
open ./dist-macos/HaizFlow.app
```

Script build tuân theo cơ chế `.app`/arm64 của [PyInstaller](https://pyinstaller.org/en/stable/usage.html). Bản này ký ad hoc cho thử nghiệm nội bộ; chưa có chữ ký Developer ID hoặc notarization để phân phối công khai.

Thư viện và model có điều kiện riêng; xem NOTICE, THIRD_PARTY_NOTICES.md và thư mục licenses/.

## Key dùng chung của team

Repo hiện private. Xem [team/README.vi.md](team/README.vi.md) và chạy `bash scripts/Nap-key-team-Mac.command` từ thư mục repo để nạp key DeepSeek/ElevenLabs, không cần dán từng key.
