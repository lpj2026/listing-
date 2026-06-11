@echo off
cd /d "%~dp0"

if "%REMOTE_SSH_PASSWORD%"=="" (
  echo 请先设置服务器 root 密码:
  echo   set REMOTE_SSH_PASSWORD=你的密码
  echo   deploy.bat
  pause
  exit /b 1
)

pip install -q paramiko requests pycryptodome 2>nul
python deploy_to_aliyun.py
pause
