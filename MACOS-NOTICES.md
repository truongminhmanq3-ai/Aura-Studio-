# Local macOS build

Aura Studio is an internal macOS application. Separately licensed components retain their own notices and terms.

CPU/vision engine and browser model weights are separate; no weights are bundled.
Native FFmpeg comes from the installed Homebrew build. Its actual licenses, formula, receipt and SBOM are in licenses/macos-ffmpeg. The original media-cli notices describe the upstream Windows build, not this native media runtime.
Keychain: keyring 25.7.0 (MIT); RAM telemetry: psutil 7.2.2 (BSD-3-Clause).
Packaging follows https://pyinstaller.org/en/stable/usage.html .
