@echo off
REM Fail closed before creating or advancing Kiro's provider-visible release branch.
REM Usage: set GH_TOKEN=... && set GITHUB_REPOSITORY=owner/repo && scripts\verify-kiro-release-source.cmd
where bash >nul 2>&1
if errorlevel 1 (
  echo Kiro release-source preflight requires Git Bash, but bash is not available. 1>&2
  exit /b 1
)
bash "%~dp0verify-kiro-release-source.sh"
exit /b %errorlevel%
