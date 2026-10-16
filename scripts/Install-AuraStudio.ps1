param([switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
$package = Split-Path -Parent $PSScriptRoot
$appSource = Join-Path $package 'app'
$keyFile = Join-Path $package 'team\team-api-keys.json'
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Aura Studio requires 64-bit Windows.' }
if (-not (Test-Path (Join-Path $appSource 'AuraStudio.exe'))) { throw 'Extract the complete Aura Studio ZIP first.' }
$config = Get-Content -LiteralPath $keyFile -Raw -Encoding UTF8 | ConvertFrom-Json
$targets = @{ deepseek='HaizFlow/DeepSeek/APIKey'; elevenlabs='HaizFlow/ElevenLabs/APIKey'; gemini='HaizFlow/Gemini/APIKey'; zernio='HaizFlow/Zernio/APIKey' }
if ($config.schema -ne 1 -or $null -eq $config.providers) { throw 'Invalid team API configuration.' }
$entries = @($config.providers.PSObject.Properties)
if ($entries.Count -eq 0) { throw 'Empty team API configuration.' }
foreach ($entry in $entries) {
 if (-not $targets.ContainsKey($entry.Name) -or -not ($entry.Value -is [string]) -or $entry.Value.Length -eq 0 -or $entry.Value -match '\s') { throw 'Invalid team API configuration.' }
}
if ($VerifyOnly) { Write-Host 'Aura Studio package and team configuration are valid. No app or credentials were installed.'; exit 0 }
if (Get-Process -Name AuraStudio,HaizFlow,HaizFlowCore -ErrorAction SilentlyContinue) { throw 'Close Aura Studio before installing.' }
Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
public static class AuraTeamCredential {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
 struct Credential {
  public uint Flags, Type;
  public string TargetName, Comment;
  public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
  public uint CredentialBlobSize;
  public IntPtr CredentialBlob;
  public uint Persist, AttributeCount;
  public IntPtr Attributes;
  public string TargetAlias, UserName;
 }
 [DllImport("advapi32.dll", EntryPoint="CredWriteW", CharSet=CharSet.Unicode, SetLastError=true)]
 static extern bool Write(ref Credential value, uint flags);
 public static void Save(string target, string value) {
  byte[] bytes=Encoding.Unicode.GetBytes(value);
  IntPtr memory=Marshal.AllocCoTaskMem(bytes.Length);
  try {
   Marshal.Copy(bytes,0,memory,bytes.Length);
   Credential credential=new Credential(); credential.Type=1; credential.TargetName=target;
   credential.CredentialBlobSize=(uint)bytes.Length; credential.CredentialBlob=memory;
   credential.Persist=2; credential.UserName="Aura Studio team";
   if(!Write(ref credential,0)) throw new Win32Exception(Marshal.GetLastWin32Error());
  } finally {
   for(int i=0;i<bytes.Length;i++) Marshal.WriteByte(memory,i,0);
   Marshal.FreeCoTaskMem(memory); Array.Clear(bytes,0,bytes.Length);
  }
 }
}
'@
$target = Join-Path $env:LOCALAPPDATA 'Programs\AuraStudio'
New-Item -ItemType Directory -Path $target -Force | Out-Null
# Overlay immutable app/engine files; preserve existing runtime data and models.
Copy-Item -Path (Join-Path $appSource '*') -Destination $target -Recurse -Force
foreach ($name in @('LICENSE','LICENSE.txt')) {
 $oldTerms=Join-Path $target $name
 if (Test-Path -LiteralPath $oldTerms -PathType Leaf) { Remove-Item -LiteralPath $oldTerms -Force }
}
foreach ($entry in $entries) { [AuraTeamCredential]::Save($targets[$entry.Name],$entry.Value) }
$shell = New-Object -ComObject WScript.Shell
$shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Aura Studio.lnk'))
$shortcut.TargetPath=Join-Path $target 'AuraStudio.exe'; $shortcut.WorkingDirectory=$target; $shortcut.Save()
Write-Host "Aura Studio installed: $target"
Write-Host 'Shared API keys were saved in Windows Credential Manager. Download required models in Settings.'
Start-Process -FilePath (Join-Path $target 'AuraStudio.exe') -WorkingDirectory $target
