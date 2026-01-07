# Build script for StreamerWidgets executable
# PowerShell version

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building StreamerWidgets.exe" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Clean previous build artifacts
Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
    Write-Host "Removed build directory" -ForegroundColor Gray
}
if (Test-Path "dist\StreamerWidgets.exe") {
    Remove-Item -Path "dist\StreamerWidgets.exe" -Force
    Write-Host "Removed previous executable" -ForegroundColor Gray
}
Write-Host ""

# Build the executable using PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Yellow
& uv run pyinstaller streamer-widgets.spec

Write-Host ""
if (Test-Path "dist\StreamerWidgets.exe") {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Executable created at: " -NoNewline
    Write-Host "dist\StreamerWidgets.exe" -ForegroundColor White
    Write-Host ""
    Write-Host "You can now run dist\StreamerWidgets.exe" -ForegroundColor Cyan
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Build failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Please check the output above for errors." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
