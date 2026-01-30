@echo off
echo ============================================
echo  Fury Cutter Labels - Premiere Pro Extension
echo  Installation Script
echo ============================================
echo.

:: Check for admin rights for registry edit
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Not running as Administrator.
    echo The registry key for debug mode may not be set.
    echo Right-click this file and "Run as administrator" for full installation.
    echo.
)

:: Enable unsigned extensions (PlayerDebugMode)
echo [1/3] Enabling unsigned extensions...
reg add "HKEY_CURRENT_USER\SOFTWARE\Adobe\CSXS.11" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul 2>&1
if %errorlevel% equ 0 (
    echo      CSXS.11 debug mode enabled
) else (
    echo      Could not set CSXS.11 - may need admin rights
)

:: Also try older CSXS versions for compatibility
reg add "HKEY_CURRENT_USER\SOFTWARE\Adobe\CSXS.10" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul 2>&1
reg add "HKEY_CURRENT_USER\SOFTWARE\Adobe\CSXS.9" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul 2>&1

:: Create extensions directory if needed
echo.
echo [2/3] Creating extensions directory...
set "EXT_DIR=%APPDATA%\Adobe\CEP\extensions"
if not exist "%EXT_DIR%" (
    mkdir "%EXT_DIR%"
    echo      Created: %EXT_DIR%
) else (
    echo      Directory exists: %EXT_DIR%
)

:: Copy extension files
echo.
echo [3/3] Installing extension...
set "DEST=%EXT_DIR%\FuryCutterLabels"

:: Remove old version if exists
if exist "%DEST%" (
    rmdir /s /q "%DEST%"
    echo      Removed old version
)

:: Copy new version
xcopy "%~dp0" "%DEST%\" /E /I /Q
echo      Installed to: %DEST%

echo.
echo ============================================
echo  Installation Complete!
echo ============================================
echo.
echo NEXT STEPS:
echo  1. Close Premiere Pro completely
echo  2. Reopen Premiere Pro
echo  3. Go to: Window ^> Extensions ^> Fury Cutter Labels
echo.
echo If the extension doesn't appear, try running this
echo script as Administrator (right-click ^> Run as administrator)
echo.
pause

