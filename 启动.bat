@echo off
chcp 65001 >nul
rem 静默启动：交给 vbs 以隐藏窗口拉起 PowerShell，全程不弹命令行黑框。
start "" wscript.exe "%~dp0启动.vbs"
exit /b
