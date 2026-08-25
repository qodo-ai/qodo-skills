@echo off
REM Create or resume a verified draft, then publish and re-verify immutable bytes.
REM Usage: set GH_TOKEN=... plus GITHUB_REPOSITORY, GITHUB_SHA, RUNNER_TEMP; then scripts\publish-release.cmd
where bash >nul 2>&1
if errorlevel 1 (
  echo Release publication requires Git Bash, but bash is not available. 1>&2
  exit /b 1
)
for /f "delims=" %%I in ('bash -lc "cygpath -u \"$RUNNER_TEMP\""') do set "RUNNER_TEMP=%%I"
bash "%~dp0publish-release.sh"
exit /b %errorlevel%
