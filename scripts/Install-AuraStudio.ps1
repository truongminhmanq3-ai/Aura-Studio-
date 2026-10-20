param([switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
$package = Split-Path -Parent $PSScriptRoot
$appSource = Join-Path $package 'app'
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Aura Studio requires 64-bit Windows.' }
if (-not (Test-Path (Join-Path $appSource 'AuraStudio.exe'))) { throw 'Extract the complete Aura Studio ZIP first.' }
if ($VerifyOnly) { Write-Host 'Aura Studio package is valid. No app was installed.'; exit 0 }
if (Get-Process -Name AuraStudio,HaizFlow,HaizFlowCore -ErrorAction SilentlyContinue) { throw 'Close Aura Studio before installing.' }
$target = Join-Path $env:LOCALAPPDATA 'Programs\AuraStudio'
New-Item -ItemType Directory -Path $target -Force | Out-Null
# Overlay immutable app/engine files; preserve existing runtime data and models.
Copy-Item -Path (Join-Path $appSource '*') -Destination $target -Recurse -Force
foreach ($name in @('LICENSE','LICENSE.txt')) {
 $oldTerms=Join-Path $target $name
 if (Test-Path -LiteralPath $oldTerms -PathType Leaf) { Remove-Item -LiteralPath $oldTerms -Force }
}
$shell = New-Object -ComObject WScript.Shell
$shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Aura Studio.lnk'))
$shortcut.TargetPath=Join-Path $target 'AuraStudio.exe'; $shortcut.WorkingDirectory=$target; $shortcut.Save()
Write-Host "Aura Studio installed: $target"
Write-Host 'Open Settings > API Key and enter your own key. Download required models in Settings.'
Start-Process -FilePath (Join-Path $target 'AuraStudio.exe') -WorkingDirectory $target
