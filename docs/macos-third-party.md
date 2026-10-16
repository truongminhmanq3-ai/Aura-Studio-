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
