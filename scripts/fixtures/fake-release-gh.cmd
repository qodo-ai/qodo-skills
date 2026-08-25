@echo off
node "%~dp0fake-release-gh.mjs" %*
exit /b %errorlevel%
