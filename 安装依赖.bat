@echo off
chcp 65001 >nul

@REM 检查 Python3 是否安装
python3 --version >nul 2>&1
if errorlevel 1 (
    echo python3 未安装
    pause
    exit /b 1
)

@REM 安装必要的包
python3 -m pip install -r requirements.txt

echo 安装完成
pause