@echo off
REM CharacterGen Launch Script

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not found! Please install Python 3.x
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Explicitly check and install required packages
python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo Installing Pillow...
    pip install Pillow
)

python -c "import yaml" >nul 2>&1
if errorlevel 1 (
    echo Installing PyYAML...
    pip install pyyaml
)

python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Installing PyQt6...
    pip install PyQt6
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installing requests...
    pip install requests
)

REM Launch application
python main.py
if errorlevel 1 (
    echo Application crashed! Check the logs for details.
    pause
)

deactivate
