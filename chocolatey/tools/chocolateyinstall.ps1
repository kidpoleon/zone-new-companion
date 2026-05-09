$ErrorActionPreference = 'Stop'

$packageName = 'zone-new-companion'
$toolsDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"
$exePath = Join-Path $toolsDir 'zone-new-companion.exe'

# Verify the executable exists
if (-not (Test-Path $exePath)) {
    throw "Executable not found at $exePath"
}

# Create shim for the executable (silent, no output)
Install-BinFile -Name $packageName -Path $exePath

# Create Start Menu shortcut using Chocolatey's helper (more reliable)
$startMenuPath = [Environment]::GetFolderPath('StartMenu')
$shortcutPath = Join-Path $startMenuPath 'Programs' 'Zone New Companion.lnk'

# Use Install-ChocolateyShortcut instead of direct COM object
$shortcutArgs = @{
    ShortcutFilePath = $shortcutPath
    TargetPath = $exePath
    WorkingDirectory = $toolsDir
    IconLocation = $exePath
    Description = 'Zone New Companion - IPTV Player'
}

Install-ChocolateyShortcut @shortcutArgs

# Suppress success messages for silent installation (verification requirement)
# Only show output in non-silent environments
if (-not $env:ChocolateyEnvironment -or $env:ChocolateyEnvironment -ne 'Verification') {
    Write-Host "Zone New Companion has been installed successfully!" -ForegroundColor Green
    Write-Host "Launch it from the Start Menu or by running 'zone-new-companion'" -ForegroundColor Green
}
