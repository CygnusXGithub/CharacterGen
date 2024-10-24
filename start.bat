@echo off
echo Checking and installing dependencies...

:: Check if pip is available
where pip >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: pip is not installed or not in PATH
    pause
    exit /b 1
)

:: Install required packages
pip install PyQt6 requests pyyaml

:: Run the program
echo Starting Character Generator...
python character_gen.py
pause