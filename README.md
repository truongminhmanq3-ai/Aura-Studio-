# Aura Studio

**Dịch, lồng tiếng và biên tập video trên Mac và Windows.**

Aura Studio là app reup video douyin, có thể làm clip thủ công, tự động và đăng hàng loạt, với giao diện Liquid Glass, nhận diện Aura Studio và tích hợp DeepSeek/ElevenLabs cho team.

Repo và các gói tải đều **private**. API DeepSeek/ElevenLabs dùng chung được giữ nguyên.

## Cài cho đồng nghiệp

Mở [trang tải Aura Studio](https://github.com/truongminhmanq3-ai/HaizFlow-macos-api/releases/tag/v0.1.8-aura-team.2) bằng tài khoản GitHub đã được cấp quyền repo, rồi chọn đúng gói:

| Máy | Gói tải | Cách cài sau khi giải nén |
| --- | --- | --- |
| Mac Apple Silicon, gồm M3; macOS 27+ | **Aura-Studio-macOS-Apple-Silicon.zip** | Chạy **Cai-dat-Aura-Studio.command** |
| Windows 10/11 x64 | **Aura-Studio-Windows-x64.zip** | Chạy **Cai-dat-Aura-Studio.cmd** |

Không cần clone source, cài Python, Homebrew hay tự build. Giải nén **toàn bộ ZIP**, giữ các thư mục đi kèm và thoát Aura Studio trước khi chạy script cài đặt.

### Mac M3 / Apple Silicon (macOS 27+)

Gói Mac hiện tại yêu cầu **macOS 27 trở lên** vì các thư viện native FFmpeg/HY-MT2 được build cho macOS 27.

Script cài app vào `~/Applications/Aura Studio.app`, nạp API chung vào macOS Keychain rồi mở app. Cho phép thao tác Keychain nếu macOS hỏi. Có thể chạy qua Terminal trong thư mục vừa giải nén:

```bash
bash Cai-dat-Aura-Studio.command
```

Nếu đã có app tại vị trí đó, bản trước được giữ làm bản sao lưu. Dữ liệu dự án nằm riêng và không bị xoá. App là bản nội bộ ký ad hoc; macOS có thể yêu cầu cho phép mở lần đầu.

### Windows

Chạy `Cai-dat-Aura-Studio.cmd` trong thư mục giải nén. Script cài app cho tài khoản Windows hiện tại, nạp cùng API vào Windows Credential Manager rồi mở Aura Studio. Không cần quyền quản trị hoặc Python. Bản Windows chưa có chữ ký Authenticode.

### Dùng lần đầu

1. Vào **Cài đặt → Gói tài nguyên**, tải Whisper và các model local cần dùng.
2. Tạo dự án, nhập video và chọn ngôn ngữ đích.
3. Chọn model dịch DeepSeek và công cụ giọng đọc ElevenLabs nếu dùng API chung; chọn giọng trong Cài đặt.
4. Kiểm tra phụ đề, giọng đọc và âm thanh trước khi xuất video.

Model weights tải riêng. Dùng DeepSeek không cần HY-MT2 cho bước dịch; dùng ElevenLabs không cần OmniVoice cho bước tạo giọng. Whisper vẫn cần cho nhận dạng. Credit, số dư và giới hạn dịch vụ được dùng chung trên tài khoản team.

## Chức năng

- Nhập video từ máy hoặc tải Douyin bằng trình duyệt tích hợp.
- Nhận dạng Whisper; dịch bằng HY-MT2 local, Gemini hoặc DeepSeek.
- Tạo giọng OmniVoice local hoặc ElevenLabs; giữ các mẫu giọng nghe thử.
- Chỉnh phụ đề, che phụ đề gốc, trộn âm thanh, watermark và xuất video.
- Xử lý tự động, thủ công, hàng loạt và tích hợp đăng bài Zernio.

## API và dữ liệu

Cấu hình dùng chung nằm trong `team/team-api-keys.json` của repo private và thư mục `team` trong gói cài. Script chỉ nạp key vào kho bảo mật của hệ điều hành; không gọi API dịch/TTS khi cài và không ghi key vào video/dự án.

Tên nội bộ `HaizFlow` trong package, executable, đường dẫn dữ liệu và mục Keychain/Credential Manager được giữ để tương thích cấu hình hiện có. Trên Mac, dữ liệu ứng dụng nằm tại `~/Library/Application Support/HaizFlow`.

Không kèm dữ liệu dự án, video cá nhân, phiên đăng nhập Douyin hoặc model weights của người dùng. Đăng nhập/captcha Douyin do người dùng thao tác trong trình duyệt của app.

Xem [hướng dẫn API cho team](team/README.vi.md) và [cấu hình API](docs/API-CONFIG.vi.md).

## Mã nguồn và build

```bash
git clone https://github.com/truongminhmanq3-ai/HaizFlow-macos-api.git
cd HaizFlow-macos-api
```

- [Build Mac](README.macos.vi.md#build-lại-trên-mac).
- `scripts/build-team-windows.py`: đóng gói Core Windows cùng runtime đã kiểm checksum.
- `src/haizflow/desktop/`: giao diện và điều khiển desktop.
- `src/haizflow/services/`, `src/haizflow/pipeline/`: dịch, giọng đọc và xử lý video.

## Thư viện và model

Giấy phép ứng dụng cũ đã được gỡ. Giấy phép độc lập của thư viện, codec, font, icon và model vẫn được giữ: [NOTICE](NOTICE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [thư viện Mac](docs/macos-third-party.md) và `licenses/`.
