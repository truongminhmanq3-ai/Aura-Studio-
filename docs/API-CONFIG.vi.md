# Cấu hình đầy đủ các API

Các tích hợp có đủ trong source. Repo private này có key DeepSeek/ElevenLabs dùng chung tại `team/team-api-keys.json`; xem [hướng dẫn nạp key tự động](../team/README.vi.md). Bạn vẫn có thể nhập key riêng tại **Cài đặt → API Key**.

## Dịch phụ đề

### DeepSeek

1. Lấy key tại [DeepSeek Platform](https://platform.deepseek.com/api_keys).
2. Mở **API Key → DeepSeek**, dán key, chọn **Lưu key**.
3. Trong **Model dịch** của dự án, chọn DeepSeek Flash hoặc DeepSeek V4 Pro.

Client gọi `POST https://api.deepseek.com/chat/completions`, dùng JSON output, tắt thinking và kiểm tra số câu/thứ tự trước khi lưu. Lưu key không gọi dịch. Phụ đề được gửi đến DeepSeek khi chạy dịch; API dùng số dư tài khoản.

### Gemini

1. Lấy key tại [Google AI Studio](https://aistudio.google.com/api-keys).
2. Mở **API Key → Gemini**, thêm tên key và key, chọn **Lưu và sử dụng**.
3. Chọn model Gemini trong dự án. Các lựa chọn khả dụng hiện tại là Gemini 3.1 Flash-Lite và Gemini 3.5 Flash-Lite; Gemini 3.8 Flash đang bị vô hiệu hóa trong giao diện.

Client sử dụng Google `generateContent`. Giữ nguyên quản lý nhiều key và key đang hoạt động của HaizFlow.

### HY-MT2 local

Không cần API key. Cài gói HY-MT2 CPU trong **Gói tài nguyên**, rồi chọn **HY-MT2 CPU · Q4** trên Mac.

## Tạo giọng

### ElevenLabs

1. Lấy key trong [ElevenLabs](https://elevenlabs.io/app/settings/api-keys).
2. Key cần quyền Text to Speech; quyền Voices cần để tải danh sách giọng.
3. Mở **API Key → ElevenLabs**, dán key, chọn **Lưu key và tải giọng**.
4. Chọn giọng từ tài khoản hoặc dán Voice ID. Chọn Flash v2.5 hoặc Eleven v3, rồi lưu giọng/model.
5. Trong dự án, chọn **ElevenLabs · API** ở công cụ giọng đọc.

Client gọi API `https://api.elevenlabs.io`, tải giọng qua `/v2/voices`, tạo MP3 qua `/v1/text-to-speech/{voice_id}`. API sử dụng credit; gói Free không dùng được giọng Voice Library qua API dù có thể thấy giọng trong danh sách. Kiểm tra [giới hạn Voice Library](https://elevenlabs.io/docs/eleven-creative/voices/voice-library).

Các đoạn MP3 hoàn tất được giữ lại để tiếp tục. Nội dung/giọng/model/ngôn ngữ thay đổi sẽ làm mất hiệu lực cache tương ứng. Yêu cầu tạo giọng lỗi không tự gửi lại.

### OmniVoice local

Không cần API key. Cài gói OmniVoice trong **Gói tài nguyên** và chọn **OmniVoice · CPU** trên Mac. Mẫu nhân bản local không tự được gửi lên ElevenLabs.

## Đăng mạng xã hội: Zernio

Mở **API Key → Zernio**, thêm key và kiểm tra kết nối. Liên kết tài khoản đích theo giao diện của HaizFlow; chọn tài khoản, nội dung và xác nhận đăng trong dự án. Client dùng `https://zernio.com/api/v1`. Phần đăng bài upstream được giữ nguyên, chưa được kiểm tra bằng một lần đăng thật trong bản Mac này.

## Chia sẻ cho đồng nghiệp

Trong repo private này, đồng nghiệp có quyền truy cập chạy script ở [thư mục team](../team/README.vi.md) để nạp hai key dùng chung vào Keychain. GitHub Secrets chỉ dành cho workflow tự động, không tự đưa key vào app desktop. Không export Keychain, cookie Douyin hoặc file dữ liệu người dùng vào source.

File [api-settings.example.json](api-settings.example.json) minh họa các lựa chọn để cấu hình trong UI; không phải file nhập tự động hay kho chứa key.
