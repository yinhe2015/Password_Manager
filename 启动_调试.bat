@echo off
chcp 65001 >nul

@REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo python 未安装
    pause
    exit /b 1
)

@REM 启动应用
python3 图形.py
pause