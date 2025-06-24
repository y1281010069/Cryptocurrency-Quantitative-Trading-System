@echo off
echo ===============================================
echo          安装系统依赖包
echo         Installing Dependencies
echo ===============================================
echo.
echo 正在安装Excel支持包 openpyxl...
pip install openpyxl
echo.
echo 正在安装其他依赖包...
pip install pandas numpy ccxt
echo.
echo 依赖包安装完成！
echo 现在可以运行专业交易系统了。
echo.
pause 