# Aura Studio

**Dịch, lồng tiếng và biên tập video trên macOS Apple Silicon.**

Aura Studio là app reup video douyin, có thể làm clip thủ công, tự động và đăng hàng loạt, với giao diện Liquid Glass, nhận diện Aura Studio và tích hợp DeepSeek/ElevenLabs cho team.

Repo này **private**, dành cho bạn và đồng nghiệp có quyền truy cập. Cấu hình API dùng chung nằm trong `team/`; khi cài trên Mac, key được nạp vào macOS Keychain.

## Tính năng

- Nhập video từ máy hoặc tải Douyin qua công cụ tích hợp.
- Nhận dạng lời thoại bằng Whisper; dịch bằng HY-MT2 local, Gemini hoặc DeepSeek.
- Tạo giọng bằng OmniVoice local hoặc ElevenLabs API; lưu công cụ và giọng theo từng dự án.
- Chỉnh phụ đề, che phụ đề gốc, trộn âm thanh, thêm watermark và xuất video.
- Xử lý tự động, thủ công hoặc hàng loạt; tích hợp đăng bài Zernio.
- Giao diện Aura Studio, biểu tượng mới, hiệu ứng chuyển trang và thông báo khi xử lý, xuất hoặc tải clip hoàn tất trong mã nguồn hiện tại.

## Cài cho thành viên trong team

Máy đích cần macOS trên **Apple Silicon (arm64)** và tài khoản GitHub có quyền truy cập repo. Repo hiện cung cấp **mã nguồn**; các release và tag cũ đã được gỡ, chưa có bộ cài mới để tải.

### 1. Đăng nhập và tải mã nguồn

```bash
gh auth login --hostname github.com
gh repo clone truongminhmanq3-ai/HaizFlow-macos-api
cd HaizFlow-macos-api
```

### 2. Build app và nạp API của team

Làm theo [hướng dẫn build trên Mac](README.macos.vi.md#build-lại-trên-mac) để tạo app từ mã nguồn hiện tại. Cần CPython 3.13, FFmpeg và các dependency được liệt kê trong hướng dẫn. Khi đã build, bản app đóng gói runtime để chạy mà không cần môi trường Python bên ngoài.

Để nạp API dùng chung, đóng app rồi chạy từ thư mục repo:

```bash
bash scripts/Nap-key-team-Mac.command
```

Cho phép truy cập Keychain nếu macOS hỏi, sau đó mở lại app. Xem [hướng dẫn API cho team](team/README.vi.md).

### 3. Chuẩn bị model và dự án

1. Vào **Cài đặt → Gói tài nguyên**, cài Whisper và các model local cần dùng. Model weights không nằm trong app.
2. Tạo dự án, nhập video và chọn ngôn ngữ đích.
3. Chọn **Model dịch** và **Công cụ giọng đọc** phù hợp, rồi chạy xử lý.
4. Kiểm tra phụ đề, giọng đọc và âm thanh trước khi xuất video.

Dùng DeepSeek sẽ không cần model HY-MT2 cho bước dịch; dùng ElevenLabs sẽ không cần model OmniVoice cho bước tạo giọng. Whisper vẫn cần cho bước nhận dạng. Demucs/OCR chỉ cần khi quy trình sử dụng đến chúng.

## API dùng chung

| Dịch vụ | Chức năng | Thiết lập |
| --- | --- | --- |
| DeepSeek | Dịch phụ đề, lưu batch để tiếp tục sau lỗi | Key team được nạp vào Keychain; chọn model DeepSeek trong dự án |
| ElevenLabs | Tải danh sách giọng và tạo giọng đọc | Key team được nạp vào Keychain; chọn giọng/model trong Cài đặt và công cụ ElevenLabs trong dự án |
| Gemini | Dịch phụ đề | Nhập key riêng trong **Cài đặt → API Key** nếu cần |
| Zernio | Kết nối tài khoản và đăng mạng xã hội | Cấu hình trong ứng dụng khi cần |

Key DeepSeek/ElevenLabs hiện có được giữ trong `team/team-api-keys.json` để team dùng chung; script nạp chúng vào Keychain trên từng Mac. Tên dịch vụ Keychain và một số đường dẫn vẫn dùng `HaizFlow` để tương thích với cấu hình sẵn có. Không cần đổi hay tạo lại key khi dùng tên Aura Studio.

Các tài khoản API dùng chung số dư, credit và giới hạn dịch vụ. Khi gặp lỗi key, quyền truy cập, hết credit hoặc giới hạn tốc độ, xử lý nguyên nhân rồi tiếp tục tác vụ. Hướng dẫn chi tiết: [cấu hình API](docs/API-CONFIG.vi.md).

## Dữ liệu và giới hạn bản Mac

- Dữ liệu ứng dụng nằm tại `~/Library/Application Support/HaizFlow`; key được lưu trong macOS Keychain trên máy chạy app.
- Mã nguồn Python tiếp tục dùng package `haizflow`; tên repo và tên asset release cũ được giữ để các lệnh tải vẫn hoạt động.
- Inference hiện chạy CPU, chưa có đường tăng tốc MPS/Metal cho Whisper/OmniVoice. Xuất H.264 ưu tiên VideoToolbox và có fallback CPU.
- Bản build đã được thử trên Apple Silicon với macOS 27.0; chưa xác nhận trên Mac Intel hoặc các phiên bản macOS khác.
- App build nội bộ ký ad hoc, chưa có Developer ID/notarization. Chưa có bản cài mới được phát hành trên GitHub.
- Model weights, video cá nhân, dữ liệu dự án và phiên đăng nhập Douyin không nằm trong repo. Đăng nhập/captcha Douyin do người dùng thao tác.
- Trong lần kiểm chứng đã ghi nhận trước đó, DeepSeek dịch được 11 câu của một clip; ElevenLabs dừng ở HTTP 402 do giới hạn tài khoản. Lần chạy đó chưa hoàn tất video đầu ra. Chi tiết kiểm chứng và build ở [README.macos.vi.md](README.macos.vi.md).

## Mã nguồn và tài liệu

| Thư mục/tài liệu | Nội dung |
| --- | --- |
| `src/haizflow/desktop/` | Giao diện Qt/QML và điều khiển desktop |
| `src/haizflow/services/` | Dịch thuật, API và các dịch vụ hỗ trợ |
| `src/haizflow/pipeline/` | Pipeline xử lý video và giọng đọc |
| `scripts/` | Tải app, nạp key, build và kiểm tra |
| `tests/` | Kiểm thử mã nguồn |
| [team/README.vi.md](team/README.vi.md) | Cài API dùng chung trên máy đồng nghiệp |
| [README.macos.vi.md](README.macos.vi.md) | Chạy app, chọn engine, build và giới hạn Mac |
| [docs/macos-third-party.md](docs/macos-third-party.md) | Thư viện native, nguồn và công thức build |

## Thư viện và model

Các thư viện, codec, font, icon và model giữ giấy phép riêng. Xem [NOTICE](NOTICE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [MACOS-NOTICES.md](MACOS-NOTICES.md) và thư mục `licenses/`.

Các mẫu nghe thử cũ có lời giới thiệu cá nhân đã được gỡ. Danh sách giọng và chức năng tạo giọng vẫn có sẵn; mẫu nghe thử trung tính có thể tạo lại bằng `scripts/generate_voice_samples.py` trong môi trường đã cài model OmniVoice.

## Với máy đã clone repo trước đây

Lịch sử Git đã được làm mới. Clone lại repo vào một thư mục mới để đồng bộ; không push lại branch hoặc tag từ bản clone cũ. Nếu có thay đổi chưa commit, sao lưu riêng các file đó trước khi chuyển sang bản clone mới.
