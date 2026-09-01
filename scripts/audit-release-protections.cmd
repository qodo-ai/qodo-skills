@echo off
setlocal
where bash >nul 2>nul || (echo Release protection audit requires Git Bash. 1>&2 & exit /b 1)
bash "%~dp0audit-release-protections.sh"
exit /b %errorlevel%
