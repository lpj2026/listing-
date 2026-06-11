@echo off

cd /d "%~dp0backend"



set APP_PORT=8001



echo Checking port %APP_PORT%...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%APP_PORT%" ^| findstr "LISTENING"') do (

  echo Stopping old listing process PID %%a

  taskkill /F /PID %%a >nul 2>&1

)



echo Starting product listing system on port %APP_PORT%...

start /MIN cmd /c "ping -n 3 127.0.0.1 >nul && start http://127.0.0.1:%APP_PORT%/create-product"

python -u app.py

if errorlevel 1 (

  echo.

  echo Failed to start. Try: pip install requests pycryptodome

  pause

)


