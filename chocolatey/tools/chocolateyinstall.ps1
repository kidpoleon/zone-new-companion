$ErrorActionPreference = 'Stop'

$packageName = 'zone-new-companion'
$toolsDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"
$exePath = Join-Path $toolsDir 'zone-new-companion.exe'

# Create shim for the executable
Install-BinFile -Name $packageName -Path $exePath

# Create Start Menu shortcut
$startMenuPath = [Environment]::GetFolderPath('StartMenu')
$shortcutPath = Join-Path $startMenuPath 'Programs' 'Zone New Companion.lnk'
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $exePath
$Shortcut.WorkingDirectory = $toolsDir
$Shortcut.IconLocation = $exePath
$Shortcut.Save()

Write-Host "Zone New Companion has been installed successfully!" -ForegroundColor Green
Write-Host "Launch it from the Start Menu or by running 'zone-new-companion'" -ForegroundColor Green
