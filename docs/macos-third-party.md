# Thư viện của bản Mac

Bản Mac chạy native arm64 với Qt/PySide, FFmpeg, Chromium và engine CPU/OCR. Các thành phần này giữ giấy phép và quyền thay thế/debug riêng.

## Nguồn và công thức build

[Release private](https://github.com/truongminhmanq3-ai/HaizFlow-macos-api/releases/tag/v0.1.8-aura-team.2) cung cấp `Aura-Studio-macOS-ThirdPartySources.zip`, chứa nguồn, công thức và manifest native đã thu thập cho bản Mac. Mã ứng dụng và script build nằm trong repo và Source code của release.

`licenses/macos-ffmpeg/` giữ license, receipt, SBOM, công thức và `source-manifest.json` ghi URL nhà cung cấp/checksum. Xem `requirements-macos-build.txt` và [hướng dẫn build Mac](../README.macos.vi.md#build-lại-trên-mac).

## Thay thế thư viện

Đóng app và tạo bản sao riêng để thử. Qt/PySide và dylib nằm trong `Contents/Frameworks`, FFmpeg/FFprobe trong `Contents/Frameworks/bin`, engine trong `Contents/Resources/engines`. Thay bằng binary arm64 tương thích, giữ tên/rpath phù hợp rồi ký lại bản sao:

```bash
codesign --force --deep --sign - "/path/to/Aura Studio.app"
codesign --verify --deep --strict "/path/to/Aura Studio.app"
"/path/to/Aura Studio.app/Contents/MacOS/HaizFlow" --macos-self-test
```

Thay Chromium cần tạo lại inventory bằng script build. Xem [hướng dẫn thay thư viện](third-party-library-replacement.md). Model weights và điều khoản model là thành phần độc lập.

## Runtime macOS 26

Tải thêm `Aura-Studio-macOS26-NativeSources.zip` ở cùng release cho runtime mới. Đây là **gói bổ sung**, dùng cùng gói nguồn Mac chung ở trên. `source-manifest.json` liệt kê chính xác phiên bản, URL, SHA256 và archive chứa từng nguồn; các nguồn chung được tham chiếu theo SHA256, các nguồn thay đổi được kèm trực tiếp. Nguồn llama-cpp-python 0.3.34 kèm toàn bộ vendor llama.cpp.

SRT 1.5.7 được build lại từ archive upstream đã kiểm SHA256 vì archive hiện tại khác checksum lịch sử trong công thức Homebrew. Cả SRT và llama dùng SDK 26.5, target 26.0; công thức và hướng dẫn build được kèm. Các binary còn lại lấy từ bottle arm64 Tahoe hoặc phiên bản cũ hơn được ghim trong `runtime/macos26-native-manifest.json`.

Thông báo và giấy phép của runtime mới nằm tại `Contents/Resources/licenses/macos26-native` trong app. Các điều khoản của thư viện và model được giữ nguyên.
