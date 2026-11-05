@echo off
rem Пересобирает данные карты (свежесть по git и файлам) и открывает её в браузере. Ничего не требует, кроме Python и Pillow.
cd /d "%~dp0"
python -X utf8 build_graph.py
start "" "%~dp0index.html"
