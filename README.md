# Aura Studio

**Video transcription, translation, AI dubbing and editing for macOS and Windows.**

Aura Studio is a desktop application for turning source video into translated, dubbed and subtitled output. The project adapts an existing Python/Qt codebase, with a focus on API integration, the desktop interface and packaging for Apple Silicon and Windows.

**Tech stack:** Python, PySide6/QML, FFmpeg, Whisper, DeepSeek and ElevenLabs.

The source code and release packages are public. API keys are not included; each user enters their own credentials in **Settings → API Key**.

## Features

- Import local video files or download Douyin videos through the built-in browser.
- Transcribe speech with Whisper; translate with local HY-MT2, Gemini or DeepSeek.
- Generate speech with local OmniVoice or ElevenLabs, with voice preview samples.
- Edit subtitles, cover original subtitles, mix audio, add watermarks and export video.
- Run manual, automatic and batch workflows, with Zernio publishing integration.

## Download and install

Open the [Aura Studio release page](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/tag/v0.1.8-aura-team.2) and choose the package for your system:

| System | Download | After extraction |
| --- | --- | --- |
| Apple Silicon Mac, including M3; macOS 26+ | [Aura-Studio-macOS26-Apple-Silicon.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-macOS26-Apple-Silicon.zip) | Run **Cai-dat-Aura-Studio.command** |
| Apple Silicon Mac, including M3; macOS 27+ | [Aura-Studio-macOS-Apple-Silicon.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-macOS-Apple-Silicon.zip) | Run **Cai-dat-Aura-Studio.command** |
| Windows 10/11 x64 | [Aura-Studio-Windows-x64.zip](https://github.com/truongminhmanq3-ai/Aura-Studio-/releases/download/v0.1.8-aura-team.2/Aura-Studio-Windows-x64.zip) | Run **Cai-dat-Aura-Studio.cmd** |

The release packages do not require a source checkout, Python, Homebrew or a local build. Extract the **entire ZIP**, keep its accompanying folders, and quit Aura Studio before running the installer.

### Apple Silicon Macs

For **macOS 26**, choose the package with `macOS26` in its filename. This package replaces the FFmpeg runtime and rebuilds the llama/SRT libraries with a macOS 26.0 deployment target. The earlier macOS 27+ package remains available.

Validation of the macOS 26 package covered architecture and minimum operating system requirements for 1,340 binaries, the interface, CPU/OCR engines, Chromium, and video export with audio and subtitles on macOS 27.2. Checks also blocked access to Homebrew. **The package has not been tested directly on a macOS 26 machine.**

The installer places the application at `~/Applications/Aura Studio.app` and opens it. Then enter your service credentials in **Settings → API Key**. You can also run the installer from Terminal inside the extracted folder:

```bash
bash Cai-dat-Aura-Studio.command
```

If an application already exists at that location, the installer keeps the previous version as a backup. Project data is stored separately and is not deleted. The application is ad hoc signed; macOS may ask you to allow it to open on first launch.

### Windows

Run `Cai-dat-Aura-Studio.cmd` from the extracted folder. The script installs Aura Studio for the current Windows account and opens it. Then enter your credentials in **Settings → API Key**. Administrator access and Python are not required. The Windows build does not have an Authenticode signature.

## First run

1. Open **Settings → Resource Packs** and download Whisper and any local models you need.
2. Create a project, import a video and choose the target language.
3. Open **Settings → API Key** and enter credentials for DeepSeek, ElevenLabs or the services you plan to use. Then choose the translation model, speech engine and voice.
4. Review the subtitles, generated speech and audio mix before exporting.

Model weights are downloaded separately. DeepSeek translation does not require HY-MT2, and ElevenLabs speech generation does not require OmniVoice. Whisper is still required for transcription. Usage charges, balances and service limits apply to each user's configured API account.

## API credentials and user data

The repository and installation packages contain no API keys or shared-key import files. The application retains the credential settings screen and integrations for DeepSeek, ElevenLabs, Gemini and Zernio. Users enter their own keys, which are stored in macOS Keychain or Windows Credential Manager. The installer does not automatically write credentials to the secure store or call external APIs.

The internal name `HaizFlow` remains in package names, executables, data paths and credential-store entries for compatibility with existing configurations. On macOS, application data is stored at `~/Library/Application Support/HaizFlow`.

User project data, personal videos, Douyin login sessions and user model weights are not included. Users handle Douyin login and CAPTCHA steps themselves in the application's browser.

See the [team API guide](team/README.vi.md) and [API configuration guide](docs/API-CONFIG.vi.md), both in Vietnamese.

## Source code and builds

```bash
git clone https://github.com/truongminhmanq3-ai/Aura-Studio-.git
cd Aura-Studio-
```

- [macOS build instructions](README.macos.vi.md#build-lại-trên-mac), in Vietnamese.
- `scripts/build-team-windows.py`: packages the Windows core with checksum-verified runtimes.
- `src/haizflow/desktop/`: desktop interface and controllers.
- `src/haizflow/services/` and `src/haizflow/pipeline/`: translation, speech generation and video processing.

## Third-party components and models

Independent licenses for libraries, codecs, fonts, icons and models are retained. See [NOTICE](NOTICE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), the [macOS component notes](docs/macos-third-party.md) and the `licenses/` directory.
