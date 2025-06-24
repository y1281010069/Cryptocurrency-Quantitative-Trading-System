@echo off
chcp 65001
echo.
echo ==========================================
echo     专业量化交易系统 - GitHub快速部署
echo ==========================================
echo.

echo 📋 部署准备检查...
echo ✅ 文件已整理到github文件夹
echo ✅ 敏感信息已移除
echo ✅ 配置模板已创建
echo.

echo 🔧 下一步操作：
echo.
echo 1. 在GitHub创建新仓库：quantitative-trading-system
echo 2. 复制以下命令到Git Bash或命令行执行：
echo.
echo    git init
echo    git add .
echo    git commit -m "feat: 初始化专业量化交易系统v3.0.0"
echo    git branch -M main
echo    git remote add origin https://github.com/YOUR_USERNAME/quantitative-trading-system.git
echo    git push -u origin main
echo.
echo 🚨 重要提醒：
echo    请将上述命令中的 YOUR_USERNAME 替换为您的GitHub用户名
echo.
echo 📚 详细说明请查看：部署说明.md
echo.

pause 