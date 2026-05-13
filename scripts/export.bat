@echo off
REM Convenience launcher for the export CLI on Windows.
REM
REM Activates the local conda env then runs `python -m balmorel_dashboard <args>`.
REM Adjust the env name with set BALMOREL_CONDA_ENV=... before calling.

setlocal
if "%BALMOREL_CONDA_ENV%"=="" set BALMOREL_CONDA_ENV=pybalmorel

call conda activate %BALMOREL_CONDA_ENV%
if errorlevel 1 (
    echo Failed to activate conda env "%BALMOREL_CONDA_ENV%".
    exit /b 1
)

cd /d "%~dp0\.."
python -m balmorel_dashboard %*
endlocal
