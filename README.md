# Aura Studio

**Dịch, lồng tiếng và biên tập video trên Mac và Windows.**

Aura Studio là ứng dụng desktop cho quy trình nhận dạng giọng nói, dịch, lồng tiếng, chỉnh phụ đề và xuất video. Dự án tùy biến một nền tảng xử lý video Python/Qt hiện có, tập trung vào tích hợp API, giao diện và đóng gói cho macOS và Windows.

**Stack:** Python, PySide6/QML, FFmpeg, Whisper, DeepSeek và ElevenLabs.

### Project overview

A desktop video workflow for transcription, translation, AI dubbing, subtitle editing and batch export. This project adapts an existing Python/Qt codebase with API integrations and packaging for Apple Silicon and Windows. Users provide their own service credentials.

Mã nguồn và các gói phát hành được công khai. Không kèm API key. Mỗi người tự nhập key của mình trong **Cài đặt → API Key**.

## Cài đặt

Mở [trang tải Aura Studio](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/tag/v0.1.8-aura-team.2), rồi chọn đúng gói:

| Máy | Gói tải | Cách cài sau khi giải nén |
| --- | --- | --- |
| Mac Apple Silicon, gồm M3; macOS 26+ | [Aura-Studio-macOS26-Apple-Silicon.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-macOS26-Apple-Silicon.zip) | Chạy **Cai-dat-Aura-Studio.command** |
| Mac Apple Silicon, gồm M3; macOS 27+ | [Aura-Studio-macOS-Apple-Silicon.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-macOS-Apple-Silicon.zip) | Chạy **Cai-dat-Aura-Studio.command** |
| Windows 10/11 x64 | [Aura-Studio-Windows-x64.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-Windows-x64.zip) | Chạy **Cai-dat-Aura-Studio.cmd** |

Không cần clone source, cài Python, Homebrew hay tự build. Giải nén **toàn bộ ZIP**, giữ các thư mục đi kèm và thoát Aura Studio trước khi chạy script cài đặt.

### Mac M3 / Apple Silicon (macOS 26 trở lên)

Máy dùng **macOS 26** chọn gói có `macOS26` trong tên. Gói này thay runtime FFmpeg và build lại thư viện llama/SRT với deployment target 26.0; không chỉ sửa nhãn phiên bản. Bản Mac cũ cho macOS 27+ vẫn có sẵn.

Bản 26 đã qua kiểm tra kiến trúc/mức tối thiểu của 1.340 binary, giao diện, CPU/OCR, Chromium và xuất video có âm thanh/phụ đề trên macOS 27.2, có kiểm tra chặn truy cập Homebrew. **Chưa chạy trực tiếp trên máy macOS 26.**

Script cài app vào `~/Applications/Aura Studio.app` rồi mở app. Sau đó tự nhập key trong **Cài đặt → API Key**. Có thể chạy qua Terminal trong thư mục vừa giải nén:

```bash
bash Cai-dat-Aura-Studio.command
```

Nếu đã có app tại vị trí đó, bản trước được giữ làm bản sao lưu. Dữ liệu dự án nằm riêng và không bị xoá. App là bản nội bộ ký ad hoc; macOS có thể yêu cầu cho phép mở lần đầu.

### Windows

Chạy `Cai-dat-Aura-Studio.cmd` trong thư mục giải nén. Script cài app cho tài khoản Windows hiện tại rồi mở Aura Studio. Sau đó tự nhập key trong **Cài đặt → API Key**. Không cần quyền quản trị hoặc Python. Bản Windows chưa có chữ ký Authenticode.

### Dùng lần đầu

1. Vào **Cài đặt → Gói tài nguyên**, tải Whisper và các model local cần dùng.
2. Tạo dự án, nhập video và chọn ngôn ngữ đích.
3. Trong **Cài đặt → API Key**, tự nhập key DeepSeek/ElevenLabs hoặc dịch vụ cần dùng. Sau đó chọn model dịch, công cụ giọng đọc và giọng của bạn.
4. Kiểm tra phụ đề, giọng đọc và âm thanh trước khi xuất video.

Model weights tải riêng. Dùng DeepSeek không cần HY-MT2 cho bước dịch; dùng ElevenLabs không cần OmniVoice cho bước tạo giọng. Whisper vẫn cần cho nhận dạng. Credit, số dư và giới hạn dịch vụ tính trên tài khoản API mà mỗi người tự cấu hình.

## Chức năng

- Nhập video từ máy hoặc tải Douyin bằng trình duyệt tích hợp.
- Nhận dạng Whisper; dịch bằng HY-MT2 local, Gemini hoặc DeepSeek.
- Tạo giọng OmniVoice local hoặc ElevenLabs; giữ các mẫu giọng nghe thử.
- Chỉnh phụ đề, che phụ đề gốc, trộn âm thanh, watermark và xuất video.
- Xử lý tự động, thủ công, hàng loạt và tích hợp đăng bài Zernio.

## API và dữ liệu

Repo và gói cài không chứa key hoặc file nạp key dùng chung. Giữ đầy đủ màn hình nhập key và các tích hợp DeepSeek, ElevenLabs, Gemini, Zernio. Mỗi người tự nhập key trong **Cài đặt → API Key**; app lưu key bằng Keychain/Credential Manager. Bộ cài không tự ghi key vào kho bảo mật hoặc gọi API.

Tên nội bộ `HaizFlow` trong package, executable, đường dẫn dữ liệu và mục Keychain/Credential Manager được giữ để tương thích cấu hình hiện có. Trên Mac, dữ liệu ứng dụng nằm tại `~/Library/Application Support/HaizFlow`.

Không kèm dữ liệu dự án, video cá nhân, phiên đăng nhập Douyin hoặc model weights của người dùng. Đăng nhập/captcha Douyin do người dùng thao tác trong trình duyệt của app.

Xem [hướng dẫn API cho team](team/README.vi.md) và [cấu hình API](docs/API-CONFIG.vi.md).

## Mã nguồn và build

```bash
git clone https://github.com/truongminhmanq3-ai/Aura-Studio-.git
cd Aura-Studio-
```

- [Build Mac](README.macos.vi.md#build-lại-trên-mac).
- `scripts/build-team-windows.py`: đóng gói Core Windows cùng runtime đã kiểm checksum.
- `src/haizflow/desktop/`: giao diện và điều khiển desktop.
- `src/haizflow/services/`, `src/haizflow/pipeline/`: dịch, giọng đọc và xử lý video.

## Thư viện và model

Giấy phép độc lập của thư viện, codec, font, icon và model vẫn được giữ: [NOTICE](NOTICE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [thư viện Mac](docs/macos-third-party.md) và `licenses/`.
