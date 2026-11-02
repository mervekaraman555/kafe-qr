@echo off
chcp 65001 >nul
title Kafe QR Siparis - Windows Kurulum Yukleyicisi
color 0E

echo ============================================================
echo   KAFE QR SIPARIS SISTEMI - WINDOWS KURULUM YUKLEYICISI
echo ============================================================
echo.

:: Proje ana dizinini bul
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%app.py" (
    set "APP_DIR=%SCRIPT_DIR%"
) else (
    for %%I in ("%SCRIPT_DIR%..\..") do set "APP_DIR=%%~fI"
)

echo [1/4] Python kurulumu kontrol ediliyor...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python bulunamadi! Lutfen https://www.python.org/downloads/ adresinden Python 3 kurun.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
echo       OK - Python bulundu.

echo [2/4] Windows Guvenlik Duvari (Firewall) port izinleri ayarlaniyor (8090 ve 8091)...
netsh advfirewall firewall add rule name="Kafe QR Musteri Port 8090" dir=in action=allow protocol=TCP localport=8090 >nul 2>&1
netsh advfirewall firewall add rule name="Kafe QR Personel Port 8091" dir=in action=allow protocol=TCP localport=8091 >nul 2>&1
echo       OK - Port izinleri tanimlandi.

echo [3/4] Masaustu "Giris Ekrani" uygulama kisayolu olusturuluyor...
set "DESKTOP=%USERPROFILE%\Desktop"
set "LAUNCHER=%DESKTOP%\Kafe_Giris_Ekrani.bat"
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
echo       OK - Masaustune "Kafe_Giris_Ekrani.bat" eklendi.

echo [4/4] Kafe sunucusu baslatiliyor ve Giris Ekrani aciliyor...
cd /d "%APP_DIR%"
netstat -ano | findstr :8091 >nul
if %errorlevel% neq 0 (
    start "" pythonw app.py
    timeout /t 2 >nul
)

echo.
echo ============================================================
echo   KURULUM TAMAMLANDI! Giris Ekrani aciliyor...
echo ============================================================
where msedge >nul 2>&1 && (start "" msedge --app=http://localhost:8091/giris & exit /b 0)
where chrome >nul 2>&1 && (start "" chrome --app=http://localhost:8091/giris & exit /b 0)
start http://localhost:8091/giris
pause

