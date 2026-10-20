"""Small Windows Credential Manager wrapper for desktop-only secrets."""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes


_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_ERROR_NOT_FOUND = 1168


class _CredentialW(ctypes.Structure):
    _fields_ = (
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    )


def _advapi32():
    if os.name != "nt":
        raise OSError("Windows Credential Manager is unavailable on this platform.")
    library = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    library.CredWriteW.argtypes = (ctypes.POINTER(_CredentialW), wintypes.DWORD)
    library.CredWriteW.restype = wintypes.BOOL
    library.CredReadW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(_CredentialW)),
    )
    library.CredReadW.restype = wintypes.BOOL
    library.CredDeleteW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD)
    library.CredDeleteW.restype = wintypes.BOOL
    library.CredFree.argtypes = (ctypes.c_void_p,)
    library.CredFree.restype = None
    return library


def write_secret(target: str, secret: str, *, username: str = "Aura Studio") -> None:
    target_name = str(target or "").strip()
    value = str(secret or "")
    if not target_name or not value:
        raise ValueError("Credential target and secret are required.")
    if sys.platform == "darwin":
        from keyring.backends.macOS import Keyring

        for service in ("AuraStudio", "HaizFlow"):
            try:
                Keyring().set_password(service, target_name, value)
            except Exception:
                pass
        return
    encoded = value.encode("utf-16-le")
    blob = (ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
    credential = _CredentialW()
    credential.Type = _CRED_TYPE_GENERIC
    credential.TargetName = target_name
    credential.CredentialBlobSize = len(encoded)
    credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = _CRED_PERSIST_LOCAL_MACHINE
    credential.UserName = str(username or "Aura Studio")
    library = _advapi32()
    if not library.CredWriteW(ctypes.byref(credential), 0):
        raise ctypes.WinError(ctypes.get_last_error())


def read_secret(target: str) -> str:
    target_name = str(target or "").strip()
    if not target_name:
        return ""
    if sys.platform == "darwin":
        env_fallback = {
            "HaizFlow/DeepSeek/APIKey": "DEEPSEEK_API_KEY",
            "HaizFlow/Gemini/APIKey": "GEMINI_API_KEY",
            "HaizFlow/ElevenLabs/APIKey": "ELEVENLABS_API_KEY",
            "AuraStudio/DeepSeek/APIKey": "DEEPSEEK_API_KEY",
            "AuraStudio/Gemini/APIKey": "GEMINI_API_KEY",
            "AuraStudio/ElevenLabs/APIKey": "ELEVENLABS_API_KEY",
        }.get(target_name)
        if env_fallback and os.getenv(env_fallback):
            return os.getenv(env_fallback, "").strip()
        from keyring.backends.macOS import Keyring

        for service in ("AuraStudio", "HaizFlow"):
            try:
                found = Keyring().get_password(service, target_name)
                if found:
                    return found
            except Exception:
                pass
        return ""
    library = _advapi32()
    pointer = ctypes.POINTER(_CredentialW)()
    if not library.CredReadW(target_name, _CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        error = ctypes.get_last_error()
        if error == _ERROR_NOT_FOUND:
            return ""
        raise ctypes.WinError(error)
    try:
        size = int(pointer.contents.CredentialBlobSize)
        if not size or not pointer.contents.CredentialBlob:
            return ""
        return ctypes.string_at(pointer.contents.CredentialBlob, size).decode("utf-16-le")
    finally:
        library.CredFree(pointer)


def delete_secret(target: str) -> bool:
    target_name = str(target or "").strip()
    if not target_name:
        return False
    if sys.platform == "darwin":
        from keyring.backends.macOS import Keyring
        from keyring.errors import PasswordDeleteError

        deleted = False
        for service in ("AuraStudio", "HaizFlow"):
            try:
                Keyring().delete_password(service, target_name)
                deleted = True
            except PasswordDeleteError:
                pass
        return deleted
    library = _advapi32()
    if library.CredDeleteW(target_name, _CRED_TYPE_GENERIC, 0):
        return True
    error = ctypes.get_last_error()
    if error == _ERROR_NOT_FOUND:
        return False
    raise ctypes.WinError(error)
