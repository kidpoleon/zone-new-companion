$ErrorActionPreference = 'Stop'

$packageName = 'zone-new-companion'

# Remove shim
Uninstall-BinFile -Name $packageName

# Remove Start Menu shortcut
$startMenuPath = [Environment]::GetFolderPath('StartMenu')
$shortcutPath = Join-Path $startMenuPath 'Programs' 'Zone New Companion.lnk'
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
}

Write-Host "Zone New Companion has been uninstalled." -ForegroundColor Green
