# Hướng dẫn Cài đặt & Sử dụng Aura Studio (v1.0 - Apple Silicon)

Ứng dụng tạo video AI tự động dành riêng cho máy Mac Apple Silicon (Chip M1, M2, M3, M4...).

---

## 1. Cách cài đặt nhanh (1-Click)

1. Nhấp đúp chuột vào tệp **`Cai-dat-Aura-Studio.command`** trong thư mục này.
2. Cửa sổ dòng lệnh Terminal sẽ tự động chạy:
   - Kiểm tra tương thích phần cứng Apple Silicon.
   - Gỡ bỏ giới hạn Gatekeeper (chống lỗi *"Ứng dụng bị hỏng / App is damaged"*).
   - Cài đặt ứng dụng vào thư mục `~/Applications/Aura Studio.app`.
   - Tự động mở Aura Studio lên màn hình.

---

## 2. Thiết lập ban đầu (Chỉ cần làm lần đầu tiên)

1. Mở ứng dụng **Aura Studio**.
2. Vào mục **Cài đặt** (biểu tượng bánh răng) → **API Key**:
   - Nhập **Gemini API Key** (Khuyên dùng để dịch video mượt mà, thông minh và nhanh nhất).
3. Bấm **Lưu**.

---

## 3. Các tính năng nổi bật trong bản v1.0

- **VieNeu-TTS Offline 48kHz:** 25 giọng đọc tiếng Việt cực kỳ tự nhiên, đầy đủ ngữ điệu Bắc, Trung, Nam; không phụ thuộc mạng, không tốn tiền API.
- **Nhân bản giọng đọc (Voice Clone):** Hỗ trợ nạp file mẫu âm thanh để mô phỏng giọng đọc theo ý muốn.
- **Tách âm thanh thông minh (Demucs):** Tự động bóc tách lời thoại cũ và giữ lại nguyên vẹn nhạc nền của video gốc.
- **Phụ đề & Che chữ Trung Quốc:** Tự động nhận diện chữ, làm mờ/vá nền thông minh và chèn phụ đề tiếng Việt chuẩn xác từng từ theo WhisperX.
