@echo off
rem Lanzador de iniciar-panel.ps1. El permiso Bypass vale solo para este proceso: no cambia la configuracion de Windows.
chcp 65001 >nul
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar-panel.ps1" %*
