@echo off
chcp 65001 >nul
title 专业交易系统主菜单

:menu
cls
echo ===============================================
echo           专业交易系统主菜单
echo        Professional Trading System
===============================================
echo.
echo 请选择要运行的系统:
echo.
echo [1] 专业交易系统 (1H+4H分析，适合波段交易)
echo [2] 多时间框架系统 (5个时间框架，适合全方位分析)
echo [3] 查看分析结果
echo [4] 退出
echo.
echo ===============================================
set /p choice=请输入选项 (1-4): 

if "%choice%"=="1" goto profit_system
if "%choice%"=="2" goto multi_system
if "%choice%"=="3" goto view_results
if "%choice%"=="4" goto exit
echo 无效选项，请重新选择...
timeout /t 2 >nul
goto menu

:profit_system
cls
echo ===============================================
echo           启动专业交易系统
echo        Professional Trading System
===============================================
echo.
echo 🎯 分析维度: 1H + 4H
echo 📊 适用场景: 波段交易 (1-7天)
echo.
call "启动专业系统.bat"
goto menu

:multi_system
cls
echo ===============================================
echo        启动多时间框架系统
echo     Multi-Timeframe System
===============================================
echo.
echo 🎯 分析维度: 周线→日线→4H→1H→15M
echo 📊 适用场景: 日内交易 + 长期投资
echo.
call "启动多时间框架系统.bat"
goto menu

:view_results
cls
call "查看分析结果.bat"
goto menu

:exit
echo.
echo 感谢使用专业交易系统！
echo.
pause
exit 