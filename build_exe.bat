@echo off
REM Build script for StreamerWidgets executable

echo ========================================
echo Building StreamerWidgets.exe
echo ========================================
echo.

REM Clean previous build artifacts
echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist\StreamerWidgets.exe" del /q "dist\StreamerWidgets.exe"
echo.

REM Build the executable using PyInstaller
echo Running PyInstaller...
uv run pyinstaller streamer-widgets.spec

echo.
if exist "dist\StreamerWidgets.exe" (
    echo ========================================
    echo Build successful!
    echo ========================================
    echo Executable created at: dist\StreamerWidgets.exe
    echo.
    echo You can now run dist\StreamerWidgets.exe
) else (
    echo ========================================
    echo Build failed!
    echo ========================================
    echo Please check the output above for errors.
    exit /b 1
)

pause
