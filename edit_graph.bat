@echo off
cd /d "%~dp0"
python -X utf8 edit_graph.py
if errorlevel 1 pause
