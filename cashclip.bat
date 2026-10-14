@echo off
chcp 65001 >nul
where py >nul 2>nul && (py -3 "%~dp0cashclip.py" %*) || (python "%~dp0cashclip.py" %*)
