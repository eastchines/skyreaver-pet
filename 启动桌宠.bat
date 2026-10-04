@echo off
chcp 65001 >nul
title SkyReaver 桌面宠物
echo ============================================
echo   SkyReaver 桌面宠物助手（零安装版）
echo   正在启动，请稍候...
echo ============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0桌宠助手.ps1"

if errorlevel 1 (
  echo.
  echo 启动遇到问题，请把上面窗口里的"红色报错文字"截图发给我。
  echo.
)
pause
