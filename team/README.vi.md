# API dùng chung của team

Repo và gói cài giữ **private**. File `team-api-keys.json` chứa cấu hình DeepSeek/ElevenLabs hiện có, được giữ nguyên để bạn và đồng nghiệp cùng dùng. Credit và giới hạn tài khoản được dùng chung.

## Cách cài đơn giản

Tải đúng gói Mac hoặc Windows tại [release](https://github.com/truongminhmanq3-ai/HaizFlow-macos-api/releases/tag/v0.1.8-aura-team.2), giải nén toàn bộ rồi chạy script cài đặt trong thư mục đó:

- Mac: `Cai-dat-Aura-Studio.command`.
- Windows: `Cai-dat-Aura-Studio.cmd`.

Script cài app và nạp key vào Keychain/Credential Manager của tài khoản hiện tại. Không cần nhập từng key, clone source hoặc cài Python. Giữ nguyên các thư mục `team` và `scripts` trong gói ZIP.

## Nạp lại trên Mac từ source

Đóng app, mở Terminal trong thư mục repo rồi chạy:

```bash
bash scripts/Nap-key-team-Mac.command
```

Cho phép thao tác Keychain khi macOS hỏi, sau đó mở lại app. Tên dịch vụ Keychain vẫn dùng HaizFlow để tương thích cấu hình hiện có.

Script không gọi API dịch/TTS, gửi video hoặc in giá trị key ra màn hình. Chọn giọng/model ElevenLabs trong Cài đặt và chọn DeepSeek/ElevenLabs trong dự án.
