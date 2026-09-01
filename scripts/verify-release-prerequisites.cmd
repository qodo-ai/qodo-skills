@echo off
REM Fail closed before a release tag or draft can be created.
REM Usage: set GH_TOKEN=... && set GITHUB_REPOSITORY=owner/repo && scripts\verify-release-prerequisites.cmd
where bash >nul 2>&1
if errorlevel 1 (
  echo Release preflight requires Git Bash, but bash is not available. 1>&2
  exit /b 1
)
bash "%~dp0verify-release-prerequisites.sh"
exit /b %errorlevel%
