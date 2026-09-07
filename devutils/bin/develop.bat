@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "scriptPath=%~dp0"
for %%I in ("%scriptPath%\..\..") do set "repoRoot=%%~fI"
set "rccPath=%scriptPath%rcc.exe"
set "rccVersion=v18.18.1"
set "rccUrl=https://github.com/joshyorko/rcc/releases/download/%rccVersion%/rcc-windows64.exe"
set "task=%~1"
if not defined task set "task=Bootstrap"

set "installedVersion="
if exist "%rccPath%" (
    for /f "usebackq delims=" %%V in (`"%rccPath%" version 2^>nul`) do set "installedVersion=%%V"
)

if not "%installedVersion%"=="%rccVersion%" (
    echo Installing RCC %rccVersion% ^(rcc-windows64.exe^)...
    where curl.exe >nul 2>&1
    if errorlevel 1 (
        powershell.exe -NoProfile -NonInteractive -Command "Invoke-WebRequest -UseBasicParsing -Uri '%rccUrl%' -OutFile '%rccPath%.download'"
    ) else (
        curl.exe --fail --location --retry 3 --silent --show-error "%rccUrl%" --output "%rccPath%.download"
    )
    if errorlevel 1 goto download_error
    move /Y "%rccPath%.download" "%rccPath%" >nul
    if errorlevel 1 goto download_error
    set "downloadedVersion="
    for /f "usebackq delims=" %%V in (`"%rccPath%" version 2^>nul`) do set "downloadedVersion=%%V"
    if not "!downloadedVersion!"=="%rccVersion%" (
        del /Q "%rccPath%"
        goto download_error
    )
)

"%rccPath%" run -r "%repoRoot%\developer\toolkit.yaml" --dev -t "%task%"
exit /b %errorlevel%

:download_error
if exist "%rccPath%.download" del /Q "%rccPath%.download"
echo RCC download failed. 1>&2
exit /b 1
