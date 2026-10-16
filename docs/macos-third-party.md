# Thư viện trong bản Mac

Bản Mac chạy native arm64, gồm Core Qt/PySide, hai engine Python CPU/OCR, Chromium và FFmpeg. Các thành phần này giữ giấy phép riêng; các quyền sửa, debug và thay thế thư viện theo giấy phép riêng được giữ nguyên.

## Nguồn và công thức build

Repo hiện chưa có release mới hoặc gói nguồn ZIP để tải. Các giấy phép, receipt, SBOM và công thức FFmpeg native nằm tại `licenses/macos-ffmpeg/`. `source-manifest.json` trong thư mục này ghi phiên bản, nguồn gốc và checksum của các đầu vào đã kiểm tra; lấy nguồn từ các URL của nhà cung cấp được ghi trong manifest.

Xem `requirements-macos-build.txt` để biết phiên bản gói Python và [hướng dẫn build Mac](../README.macos.vi.md#build-lại-trên-mac) để tạo app. Khi phát hành binary mới, đóng gói và cung cấp nguồn tương ứng của các thư viện theo giấy phép của từng thành phần.

## Thay thế thư viện trên Mac

1. Đóng app, tạo một bản sao `HaizFlow.app` riêng để thử.
2. Build thư viện arm64 với phiên bản/API tương thích. Qt/PySide nằm trong `Contents/Frameworks/PySide6`, các dylib trong `Contents/Frameworks`; FFmpeg/FFprobe nằm trong `Contents/Frameworks/bin`. Engine nằm dưới `Contents/Resources/engines`; PyAV 19.0.1 trên Mac dùng các dylib FFmpeg 9 và x264/x265 của wheel, không phải backend LGPL-only Windows được mô tả ở tài liệu upstream. Nguồn PyAV và các thư viện này được ghi riêng trong gói nguồn Mac.
3. Thay đúng framework/dylib, binding hoặc executable trong bản sao. Giữ kiến trúc, tên thư viện và rpath tương thích; thay đổi ABI có thể cần build lại PySide hoặc app.
4. Ký ad hoc bản sao sau khi sửa, không cần khóa ký của nhà phát hành:

   ```bash
   codesign --force --deep --sign - /path/to/HaizFlow.app
   codesign --verify --deep --strict /path/to/HaizFlow.app
   PATH=/usr/bin:/bin /path/to/HaizFlow.app/Contents/MacOS/HaizFlow --macos-self-test
   ```

Chromium có kiểm tra inventory trong app; nếu thay browser, cần tạo lại inventory bằng script build thay vì chỉ chép executable. Đọc [hướng dẫn build Mac](../README.macos.vi.md) và [tài liệu thay thư viện upstream](third-party-library-replacement.md). Nguồn ứng dụng cũng chạy trực tiếp với môi trường Python/PySide đã sửa. Tính tương thích của thư viện thay thế phải được kiểm tra trên bản sao; bản Mac này không có Developer ID/notarization.
