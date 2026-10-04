@echo off
chcp 65001 >nul
echo ============================================
echo   SkyReaver 桌宠一键打包脚本 (Windows)
echo ============================================
echo.

echo [1/3] 安装依赖...
pip install pynput pywin32 pyinstaller
if errorlevel 1 ( echo 依赖安装失败，请检查网络或 Python 环境 & pause & exit /b 1 )

echo [2/3] 开始打包为单个 exe...
pyinstaller -w -F --clean --add-data "beast_body.png;." --add-data "beast_hand.png;." --add-data "girl_body.png;." --add-data "girl_hand.png;." main.py -n "SkyReaver桌宠"
if errorlevel 1 ( echo 打包失败，请查看上方报错信息 & pause & exit /b 1 )

echo [3/3] 打包完成！
echo.
echo 成品位置：dist\SkyReaver桌宠.exe
echo 双击该 exe 即可运行，无需安装 Python。
echo.
pause
