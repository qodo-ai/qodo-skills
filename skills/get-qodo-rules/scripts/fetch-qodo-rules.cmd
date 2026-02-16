@echo off
REM Wrapper script that detects available Python interpreter and runs the fetch script
REM This ensures compatibility across Windows systems that have either python3, python, or py

setlocal

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%fetch-qodo-rules.py"

REM Detect available Python interpreter
REM Try py launcher first (recommended for Windows)
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py -3 "%PYTHON_SCRIPT%" %*
    exit /b %ERRORLEVEL%
)

REM Try python3 command
where python3 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python3 "%PYTHON_SCRIPT%" %*
    exit /b %ERRORLEVEL%
)

REM Try python command and verify it's Python 3
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    REM Check if it's Python 3
    for /f "delims=" %%i in ('python -c "import sys; print(sys.version_info[0])" 2^>nul') do set PYTHON_VERSION=%%i
    if "%PYTHON_VERSION%"=="3" (
        python "%PYTHON_SCRIPT%" %*
        exit /b %ERRORLEVEL%
    )
)

REM No Python 3 found
echo Warning: Python 3 is required but not found. Please install Python 3:
echo    - Download from https://www.python.org/downloads/
echo    - Make sure to check "Add Python to PATH" during installation
exit /b 0