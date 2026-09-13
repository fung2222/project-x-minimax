@echo off
cd /d "%~dp0"
python3.12 -m http.server 8080
