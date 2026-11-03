@echo off
chcp 65001 >nul
title Kafe QR Siparis - Windows Kurulum Yukleyicisi
color 0E

echo ============================================================
echo   KAFE QR SIPARIS SISTEMI - WINDOWS KURULUM YUKLEYICISI
echo ============================================================
echo.

set "CLOUD_URL=https://faruk8503.pythonanywhere.com/giris"
set "SCRIPT_DIR=%~dp0"
set "APP_DIR="

if exist "%SCRIPT_DIR%app.py" (
    set "APP_DIR=%SCRIPT_DIR%"
) else (
    for %%I in ("%SCRIPT_DIR%..\..") do (
        if exist "%%~fI\app.py" set "APP_DIR=%%~fI"
    )
)

set "DESKTOP=%USERPROFILE%\Desktop"
set "LAUNCHER=%DESKTOP%\Kafe_Giris_Ekrani.bat"

if defined APP_DIR (
    echo [1/3] Windows Guvenlik Duvari port izinleri ayarlaniyor (8090 ve 8091)...
    netsh advfirewall firewall add rule name="Kafe QR Musteri Port 8090" dir=in action=allow protocol=TCP localport=8090 >nul 2>&1
    netsh advfirewall firewall add rule name="Kafe QR Personel Port 8091" dir=in action=allow protocol=TCP localport=8091 >nul 2>&1
    echo [2/3] Masaustune Kafe_Giris_Ekrani kisayolu olusturuluyor...
    (
    echo @echo off
    echo cd /d "%APP_DIR%"
    echo netstat -ano ^| findstr :8091 ^>nul
    echo if %%errorlevel%% neq 0 ^(
    echo     start "" pythonw app.py
    echo     timeout /t 2 ^>nul
    echo ^)
    echo where msedge ^>nul 2^>^&1 ^&^& ^(start "" msedge --app=http://localhost:8091/giris ^& exit^)
    echo where chrome ^>nul 2^>^&1 ^&^& ^(start "" chrome --app=http://localhost:8091/giris ^& exit^)
    echo start http://localhost:8091/giris
    ) > "%LAUNCHER%"
    echo [3/3] Kafe sunucusu baslatiliyor ve Giris Ekrani aciliyor...
    cd /d "%APP_DIR%"
    netstat -ano | findstr :8091 >nul
    if %errorlevel% neq 0 (
        start "" pythonw app.py
        timeout /t 2 >nul
    )
    where msedge >nul 2>&1 && (start "" msedge --app=http://localhost:8091/giris & exit /b 0)
    where chrome >nul 2>&1 && (start "" chrome --app=http://localhost:8091/giris & exit /b 0)
    start http://localhost:8091/giris
) else (
    echo [1/2] Bulut baglantili Masaustu Uygulama kisayolu olusturuluyor...
    (
    echo @echo off
    echo where msedge ^>nul 2^>^&1 ^&^& ^(start "" msedge --app=%CLOUD_URL% ^& exit^)
    echo where chrome ^>nul 2^>^&1 ^&^& ^(start "" chrome --app=%CLOUD_URL% ^& exit^)
    echo start %CLOUD_URL%
    ) > "%LAUNCHER%"
    echo [2/2] Kafe Yonetim Giris Ekrani aciliyor...
    where msedge >nul 2>&1 && (start "" msedge --app=%CLOUD_URL% & exit /b 0)
    where chrome >nul 2>&1 && (start "" chrome --app=%CLOUD_URL% & exit /b 0)
    start %CLOUD_URL%
)
