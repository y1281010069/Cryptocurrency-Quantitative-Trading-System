@echo off
chcp 65001 >nul
echo ===============================================
echo        多时间框架专业投资系统
echo     Multi-Timeframe Professional System
echo ===============================================
echo.
echo 分析维度: 周线-日线-4H-1H-15M
echo 适用场景: 日内交易 + 长期投资
echo.
echo 正在启动系统...
echo.

cd /d "%~dp0"

python multi_timeframe_system.py

echo.
echo 系统运行完成！
echo 请查看multi_timeframe_reports文件夹中的结果
echo.
pause 