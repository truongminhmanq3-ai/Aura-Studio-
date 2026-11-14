"""Build native Core.app and isolated CPU/vision engines on macOS.

Run with the project's Python 3.13 venv after installing its native dependencies.
No Windows assets, runtime paths, or CUDA libraries enter this build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def run(command, **kwargs):
    print("Running:", " ".join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def add_engine_resources(target: Path, profile: str):
    import importlib.metadata
    from PyInstaller.utils.hooks import collect_data_files

    internal = target / "_internal"
    # Inference libraries query dependency versions at runtime. Include the
    # installed distribution records even for imports invisible to analysis.
    for distribution in importlib.metadata.distributions():
        source = Path(distribution._path)
        if source.is_dir() and source.name.endswith(".dist-info") and distribution.metadata["Name"].lower() not in {"haizflow", "aura-studio"}:
            shutil.copytree(source, internal / source.name, dirs_exist_ok=True)
    if profile == "cpu":
        for package in ("pyannote.audio", "pyannote.database", "pyannote.pipeline", "lightning", "pytorch_lightning", "lightning_fabric"):
            for source, destination in collect_data_files(package):
                dest = internal / destination / Path(source).name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)


def engine_spec(profile: str, build: Path):
    extra = (["torch", "torchaudio", "torchvision", "whisperx", "faster_whisper", "demucs",
              "llama_cpp", "transformers", "accelerate", "soundfile", "soxr", "nltk", "av",
              "pyannote.audio.models.segmentation.PyanNet", "pydub.silence", "torchcodec",
              "transformers.models.higgs_audio_v2_tokenizer", "transformers.models.auto",
              "sherpa_onnx", "requests"]
             if profile == "cpu" else ["onnxruntime", "rapidocr"])
    excludes = ["PySide6", "playwright", "pytest", "IPython", "notebook", "jupyter",
                "tensorflow", "jax", "tensorboard", "triton", "cupy"]
    if profile == "vision":
        excludes.extend(["torch", "torchaudio", "torchvision", "whisperx", "pyannote",
                         "demucs", "transformers", "llama_cpp", "faster_whisper", "torchcodec"])
    packages = (["whisperx", "faster_whisper", "llama_cpp", "transformers", "demucs"]
                if profile == "cpu" else ["rapidocr"])
    spec = build / f"engine-{profile}.spec"
    spec.write_text(f'''
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata
datas = []
for package in {packages!r}:
    datas += collect_data_files(package, include_py_files=(package == 'transformers'))
hidden = collect_submodules('haizflow', filter=lambda n: not n.startswith(('haizflow.desktop', 'haizflow.main', 'haizflow.update')))
hidden += {extra!r}
if {profile!r} == 'cpu':
    hidden += collect_submodules('whisperx') + collect_submodules('demucs')
    hidden += ['einops', 'safetensors.torch', 'huggingface_hub']
for name in {(['torch', 'torchaudio', 'torchvision', 'whisperx', 'faster-whisper', 'demucs', 'llama-cpp-python', 'transformers', 'accelerate', 'huggingface-hub', 'sherpa-onnx'] if profile == 'cpu' else ['onnxruntime', 'rapidocr'])!r}:
    datas += copy_metadata(name)
a = Analysis([{str(ROOT / 'scripts/macos-engine-entry.py')!r}], pathex=[{str(ROOT / 'src')!r}],
             binaries=[], datas=datas, hiddenimports=hidden, excludes={excludes!r},
             hookspath=[], runtime_hooks=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='HaizFlowEngine', console=True,
          target_arch={platform.machine()!r}, codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, name='HaizFlowEngine', strip=False, upx=False)
''')
    return spec


def core_spec(build: Path, ffmpeg: str, ffprobe: str, min_macos: str = "14.0"):
    spec = build / "HaizFlow.spec"
    spec.write_text(f'''
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata
datas = [(str({str(ROOT / 'src/haizflow/desktop/qml')!r}), 'haizflow/desktop/qml'),
         (str({str(ROOT / 'src/haizflow/desktop/assets')!r}), 'haizflow/desktop/assets'),
         (str({str(ROOT / 'src/haizflow/desktop/translations')!r}), 'haizflow/desktop/translations'),
         (str({str(ROOT / 'src/haizflow/assets/fonts')!r}), 'haizflow/assets/fonts')]
datas += collect_data_files('certifi') + collect_data_files('playwright') + collect_data_files('vieneu') + collect_data_files('sea_g2p') + collect_data_files('sherpa_onnx')
datas += copy_metadata('playwright') + copy_metadata('aura-studio') + copy_metadata('vieneu') + copy_metadata('sea_g2p') + copy_metadata('sherpa-onnx')
hidden = collect_submodules('haizflow') + collect_submodules('yt_dlp') + collect_submodules('vieneu', filter=lambda n: 'serve' not in n) + collect_submodules('sea_g2p') + ['keyring.backends.macOS', 'psutil', 'soxr', 'kaldi_native_fbank', 'soundfile', 'requests', 'sherpa_onnx']
excluded = ['torch', 'torchaudio', 'torchvision', 'whisperx', 'pyannote', 'torchcodec',
            'transformers', 'accelerate', 'llama_cpp', 'ctranslate2', 'faster_whisper', 'demucs',
            'rapidocr', 'av', 'matplotlib', 'IPython', 'pytest',
            'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineQuick', 'PySide6.QtWebEngineWidgets',
            'PySide6.QtQuick3D', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtCharts']
a = Analysis([{str(ROOT / 'haizflow_desktop.py')!r}], pathex=[{str(ROOT / 'src')!r}],
             binaries=[({ffmpeg!r}, 'bin'), ({ffprobe!r}, 'bin')], datas=datas,
             hiddenimports=hidden, excludes=excluded, hookspath=[], runtime_hooks=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Aura Studio', console=False,
          target_arch={platform.machine()!r}, codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, name='Aura Studio', strip=False, upx=False)
app = BUNDLE(coll, name='Aura Studio.app', icon={str(ROOT / 'src/haizflow/desktop/assets/branding/AuraStudio.icns')!r},
             bundle_identifier='dev.aurastudio.macos.local', version={VERSION!r},
             info_plist={{'CFBundleDisplayName': 'Aura Studio', 'CFBundleName': 'Aura Studio',
                         'CFBundleExecutable': 'Aura Studio', 'CFBundleShortVersionString': {VERSION!r},
                         'NSHighResolutionCapable': True, 'LSMinimumSystemVersion': {min_macos!r},
                         'NSMicrophoneUsageDescription': 'Aura Studio sử dụng âm thanh khi bạn chọn công cụ giọng đọc.'}})
''')
    return spec


def _version(text):
    return tuple(int(part) for part in text.split("."))


def lower_minos(app: Path, target: str):
    """Rewrite the minimum-OS field of bundled Mach-O files built for a newer point release of the same major
    macOS (for example libtesseract needing 26.6.2 when the app must start on 26.0). Refuses anything that
    needs a newer major version (except the llama.cpp libraries), since that cannot be fixed by relabeling."""
    wanted = _version(target)
    for path in sorted(app.rglob("*")):
        if path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK):
            continue
        info = subprocess.run(["vtool", "-show-build", path], capture_output=True, text=True)
        if info.returncode != 0:
            continue
        fields = dict(line.strip().split(None, 1) for line in info.stdout.splitlines() if " " in line.strip())
        if "minos" not in fields or "sdk" not in fields:
            continue
        have = _version(fields["minos"].strip())
        if have <= wanted:
            continue
        # llama.cpp ships labeled for the build machine's macOS but its imports were checked against the
        # macOS 26.5 SDK (no 27-only system symbol); every other newer-major binary is still refused.
        if have[0] != wanted[0] and "llama_cpp/lib/" not in path.as_posix():
            raise SystemExit(f"{path} needs macOS {fields['minos']}; it cannot run on macOS {target}.")
        patched = path.with_name(path.name + ".minos")
        run(["vtool", "-set-build-version", "macos", target, fields["sdk"].strip(), "-replace", "-output", patched, path])
        patched.replace(path)
        print(f"Lowered minimum macOS {fields['minos']} -> {target}: {path.relative_to(app)}", flush=True)


def bundle_ffmpeg_omp(app: Path):
    """FFmpeg's whisper/ggml library needs the current Homebrew libomp, but the app already carries an older
    scikit-learn libomp under the same name. Ship the matching one under its own name and point only ggml at it."""
    frameworks = app / "Contents/Frameworks"
    ggml = frameworks / "libggml-base.0.dylib"
    source = Path("/opt/homebrew/opt/libomp/lib/libomp.dylib")
    if not ggml.is_file():
        return
    if not source.is_file():
        raise SystemExit("Homebrew libomp is required to bundle FFmpeg.")
    target = frameworks / "libomp-ffmpeg.dylib"
    shutil.copy2(source, target, follow_symlinks=True)
    target.chmod(0o755)
    run(["install_name_tool", "-id", "@rpath/libomp-ffmpeg.dylib", target])
    run(["install_name_tool", "-change", "@rpath/libomp.dylib", "@loader_path/libomp-ffmpeg.dylib", ggml])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", type=Path, help="Owned Playwright chromium-1243 directory")
    parser.add_argument("--reuse-bundle", type=Path, help="Reuse verified native engines and browser from an existing Mac app")
    parser.add_argument("--skip-engines", action="store_true", help="Reuse already-built engines")
    parser.add_argument("--reuse-cpu", action="store_true", help="Reuse a compiled CPU engine, then verify its resources")
    parser.add_argument("--min-macos", default="14.0", help="Minimum macOS written to Info.plist. A value of 26.x "
                        "also lowers bundled libraries that were built for a newer 26.x point release")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip browser and UI smoke tests")
    args = parser.parse_args()
    if sys.platform != "darwin" or sys.version_info[:2] != (3, 13):
        parser.error("Build on macOS using CPython 3.13.")
    if args.reuse_bundle:
        args.skip_engines = True
        args.browser = args.reuse_bundle / "Contents/Resources/mac-browser"
        if not args.browser.is_dir():
            parser.error("The reuse bundle is missing its native browser.")
    if not args.browser:
        parser.error("Provide --browser or --reuse-bundle.")
    args.output.mkdir(parents=True, exist_ok=True)
    build = ROOT / "build-macos"
    build.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update({"PYTHONPATH": str(ROOT / "src"), "HAIZFLOW_HOME": str(build / "runtime"),
                "USE_TORCH": "1", "USE_TF": "0", "PYINSTALLER_CONFIG_DIR": str(build / "pyinstaller-cache")})
    for profile in ("cpu", "vision"):
        if args.skip_engines:
            continue
        if not (args.reuse_cpu and profile == "cpu"):
            run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", build / f"dist-{profile}",
                 "--workpath", build / f"work-{profile}", engine_spec(profile, build)], env=env)
        add_engine_resources(build / f"dist-{profile}/HaizFlowEngine", profile)
        executable = build / f"dist-{profile}/HaizFlowEngine/HaizFlowEngine"
        run([executable, "--smoke", "--profile", profile], env={**env, "PATH": "/usr/bin:/bin"}, timeout=180)
    full = Path("/opt/homebrew/opt/ffmpeg-full/bin")
    ffmpeg, ffprobe = (str(full / name) if (full / name).is_file() else shutil.which(name) for name in ("ffmpeg", "ffprobe"))
    if not ffmpeg or not ffprobe:
        parser.error("FFmpeg and FFprobe are required to build; both are bundled into the app.")
    filters = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, check=True).stdout
    if not all(name in filters for name in (" ass ", " drawtext ")):
        parser.error("FFmpeg must include libass and drawtext. Install Homebrew ffmpeg-full.")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", args.output,
         "--workpath", build / "work-core", core_spec(build, ffmpeg, ffprobe, args.min_macos)], env=env)
    app = args.output / "Aura Studio.app"
    resources = app / "Contents/Resources"
    for profile, pack_id in (("cpu", "engine-cpu-py313"), ("vision", "engine-vision-onnx")):
        target = resources / "engines" / pack_id / "1"
        source = (args.reuse_bundle / "Contents/Resources/engines" / pack_id / "1"
                  if args.reuse_bundle else build / f"dist-{profile}/HaizFlowEngine")
        shutil.copytree(source, target, symlinks=True)
        base = ["HaizFlowEngine"]
        engine = {"pack_id": pack_id, "profile": profile, "version": "1", "protocol_version": 1,
                  "runtime_contract": 6 if profile == "cpu" else 0,
                  "smoke_command": base + ["--smoke", "--profile", profile], "rpc_command": base + ["--rpc"],
                  "hymt2_server": base + ["--hymt2-worker", "--server"],
                  "omnivoice_worker": base + ["--omnivoice-worker"], "omnivoice_server": base + ["--omnivoice-server"],
                  "demucs": base + ["--demucs-separate"], "demucs_task": base, "transcribe": base,
                  "subtitle_ocr": base, "runtime_probe": base + ["--runtime-probe"]}
        write_json(target / "engine.json", engine)
        write_json(target / "complete.json", {"schema": 1, "pack_id": pack_id, "version": "1", "protocol_version": 1})
    browser = resources / "mac-browser"
    shutil.copytree(args.browser, browser, symlinks=True)
    sys.path.insert(0, str(ROOT / "src"))
    from haizflow.services.douyin_component import write_inventory, file_digest, smoke, REVISION, PACK_ID
    # Signing happens before inventory: it changes Mach-O and signature resources.
    # Protect against dyld collisions between bundled sklearn libomp and ffmpeg/ffprobe
    for bin_name in ("ffmpeg", "ffprobe"):
        target = app / "Contents/Frameworks/bin" / bin_name
        if target.parent.is_dir():
            native = target.with_name(bin_name + "-native")
            if not native.exists() and target.exists() and target.read_bytes()[:2] != b"#!":
                target.rename(native)  # the real FFmpeg collected by PyInstaller, with its libraries
            if not native.exists():
                raise SystemExit(f"Bundled {bin_name} is missing; the app would depend on Homebrew.")
            target.write_text(f"""#!/bin/sh
unset DYLD_LIBRARY_PATH
unset DYLD_FALLBACK_LIBRARY_PATH
unset DYLD_FRAMEWORK_PATH
exec "$(dirname "$0")/{bin_name}-native" "$@"
""", encoding="utf-8")
            target.chmod(0o755)
    bundle_ffmpeg_omp(app)
    run(["codesign", "--force", "--deep", "--sign", "-", app])
    write_inventory(browser)
    write_json(browser / "complete.json", {"pack_id": PACK_ID, "version": REVISION,
               "platform": "darwin-" + platform.machine(), "browser_inventory_sha256": file_digest(browser / "browser-files.json")})
    for filename in ("NOTICE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / filename, resources / filename)
    if (ROOT / "LICENSE").is_file():
        shutil.copy2(ROOT / "LICENSE", resources / "LICENSE")
    shutil.copytree(ROOT / "licenses", resources / "licenses", symlinks=True)
    sea_g2p_bin = ROOT / ".venv/lib/python3.13/site-packages/sea_g2p/sea_g2p.bin"
    if sea_g2p_bin.is_file():
        for dest in (app / "Contents/Frameworks/sea_g2p", resources / "sea_g2p"):
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sea_g2p_bin, dest / "sea_g2p.bin")
    ffmpeg_prefix = Path(ffmpeg).resolve().parents[1]
    native_licenses = resources / "licenses/macos-ffmpeg"
    native_licenses.mkdir(parents=True, exist_ok=True)
    for path in ffmpeg_prefix.glob("COPYING*"):
        shutil.copy2(path, native_licenses / path.name)
    for filename in ("LICENSE.md", "INSTALL_RECEIPT.json", "sbom.spdx.json"):
        if (ffmpeg_prefix / filename).is_file():
            shutil.copy2(ffmpeg_prefix / filename, native_licenses / filename)
    for formula in (ffmpeg_prefix / ".brew").glob("*.rb"):
        shutil.copy2(formula, native_licenses / formula.name)
    (resources / "MACOS-NOTICES.md").write_text(
        "# Aura Studio macOS build\n\nAura Studio " + VERSION +
        ". Separately licensed components retain their own notices and terms.\n\n"
        "CPU/vision engine and browser model weights are separate; no weights are bundled.\n"
        "Native FFmpeg is the Homebrew ffmpeg-full build copied into the app together with its libraries. Its actual licenses, formula, "
        "receipt and SBOM are in licenses/macos-ffmpeg. The original media-cli notices describe "
        "the upstream Windows build, not this native media runtime.\n"
        "Keychain: keyring 25.7.0 (MIT); RAM telemetry: psutil 7.2.2 (BSD-3-Clause).\n"
        "Packaging follows https://pyinstaller.org/en/stable/usage.html .\n")
    write_json(resources / "BUILD-INFO.json", {"application": "HaizFlow", "version": VERSION,
               "platform": "darwin-" + platform.machine(), "build": "local macOS port; unofficial"})
    (app / "Contents/MacOS/BUILD-INFO.json").symlink_to("../Resources/BUILD-INFO.json")
    macos_bin = app / "Contents/MacOS/bin"
    if macos_bin.is_symlink() or macos_bin.exists():
        if macos_bin.is_symlink():
            macos_bin.unlink()
        else:
            shutil.rmtree(macos_bin)
    macos_bin.symlink_to("../Frameworks/bin")
    # Protect against dyld collisions between bundled sklearn libomp and ffmpeg/ffprobe
    for bin_name in ("ffmpeg", "ffprobe"):
        target = app / "Contents/Frameworks/bin" / bin_name
        if target.parent.is_dir():
            native = target.with_name(bin_name + "-native")
            if not native.exists() and target.exists() and target.read_bytes()[:2] != b"#!":
                target.rename(native)  # the real FFmpeg collected by PyInstaller, with its libraries
            if not native.exists():
                raise SystemExit(f"Bundled {bin_name} is missing; the app would depend on Homebrew.")
            target.write_text(f"""#!/bin/sh
unset DYLD_LIBRARY_PATH
unset DYLD_FALLBACK_LIBRARY_PATH
unset DYLD_FRAMEWORK_PATH
exec "$(dirname "$0")/{bin_name}-native" "$@"
""", encoding="utf-8")
            target.chmod(0o755)
    if _version(args.min_macos) >= (26, 0):
        lower_minos(app, args.min_macos)
    run(["codesign", "--force", "--deep", "--sign", "-", app])
    # Codesign changes browser resources: publish the final checksum inventory.
    write_inventory(browser)
    write_json(browser / "complete.json", {"pack_id": PACK_ID, "version": REVISION,
               "platform": "darwin-" + platform.machine(), "browser_inventory_sha256": file_digest(browser / "browser-files.json")})
    # Seal new metadata without modifying the already-signed nested Chromium.
    run(["codesign", "--force", "--sign", "-", app])
    if not args.skip_smoke:
        smoke(browser)
        run([app / "Contents/MacOS/Aura Studio", "--ui-smoke-test"], env={**env, "PATH": "/usr/bin:/bin", "HAIZFLOW_SMOKE_TEST": "1"}, timeout=90)
    print("Built and verified:", app, flush=True)


if __name__ == "__main__":
    main()
