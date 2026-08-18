@echo off
title Arabic RTL Fixer v2
cd /d "%~dp0"
echo ========================================
echo   Arabic RTL Fixer v2 - Affinity Tool
echo ========================================
echo.
echo Checking dependencies...
pip install arabic-reshaper python-bidi pyperclip pyautogui keyboard --quiet 2>nul
echo.
echo Starting Arabic RTL Fixer...
python arabic_fixer.py
if errorlevel 1 (
    echo.
    echo [ERROR] Something went wrong. Make sure Python 3 is installed.
    pause
)
