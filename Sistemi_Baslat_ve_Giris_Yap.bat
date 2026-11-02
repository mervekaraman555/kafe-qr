@echo off
cd /d "%~dp0"
netstat -ano | findstr :8091 >nul
if %errorlevel% neq 0 (
    start "" pythonw app.py
    timeout /t 2 >nul
)
where msedge >nul 2>&1 && (start "" msedge --app=http://localhost:8091/giris & exit /b 0)
where chrome >nul 2>&1 && (start "" chrome --app=http://localhost:8091/giris & exit /b 0)
start http://localhost:8091/giris

