@echo off
chcp 65001 >nul
echo ===============================================
echo           专业交易系统启动器
echo        Professional Trading System
echo ===============================================
echo.
echo 正在启动专业交易系统...
echo.

cd /d "%~dp0"

python ultimate_profit_system.py

echo.
echo 系统运行完成！
echo 请查看分析报告文件夹中的结果文件
echo.
pause 