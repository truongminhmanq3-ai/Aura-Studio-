# Key dùng chung của team

Repo này giữ **private**. `team-api-keys.json` chứa key thật của DeepSeek và ElevenLabs đang lưu trên máy chủ repo, được chia sẻ cho team theo yêu cầu. Gemini/Zernio chưa có key nên không nằm trong file. OmniVoice, Whisper và HY-MT2 dùng model local, không cần key.

Trên Mac của đồng nghiệp:

1. Được cấp quyền repo, đăng nhập GitHub và clone hoặc tải ZIP mã nguồn của nhánh hiện tại.
2. Đóng Aura Studio. Mở Terminal tại thư mục repo, chạy:

   ```bash
   bash scripts/Nap-key-team-Mac.command
   ```

3. Nếu macOS hỏi quyền Keychain, cho phép thao tác nạp key. Mở lại Aura Studio; các key đã được nạp vào mục Keychain mang tên HaizFlow để tương thích với cấu hình hiện có. Không cần dán từng key, không cần Python/Homebrew và không cần build lại app.
4. Trong dự án, chọn DeepSeek và ElevenLabs theo nhu cầu. Giọng/model ElevenLabs vẫn chọn trong Cài đặt; credit được dùng chung trên tài khoản của team.

Script chỉ ghi key của các provider có trong file; không gửi video hoặc gọi API dịch/TTS. File key không được nhúng vào bản app đã phát hành trước đó. Chỉ người có quyền repo mới tải được cấu hình này.

Repo hiện chỉ có mã nguồn; các release và tag cũ đã được gỡ. Tạo app theo [hướng dẫn build Mac](../README.macos.vi.md#build-lại-trên-mac), rồi nạp key như trên. API/key của team không thay đổi khi làm mới lịch sử Git.

Nếu đã clone repo trước khi lịch sử được làm mới, clone lại vào thư mục mới. Không push lại branch/tag từ bản clone cũ.
