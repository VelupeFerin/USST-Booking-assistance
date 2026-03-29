@echo off
cd /d %~dp0
call activate
python run_server.py
pause