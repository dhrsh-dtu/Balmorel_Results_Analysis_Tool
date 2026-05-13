@echo off
REM Convenience launcher for local dev on Windows.
REM
REM Activates an existing conda env (default name: pybalmorel) and runs the
REM Streamlit dashboard. Pass a different env name as the first argument.

setlocal
set ENV_NAME=pybalmorel
set PORT=8501

if not "%~1"=="" set ENV_NAME=%~1
if not "%~2"=="" set PORT=%~2

call conda activate %ENV_NAME%
if errorlevel 1 (
    echo Failed to activate conda env "%ENV_NAME%".
    exit /b 1
)

cd /d "%~dp0\.."
streamlit run streamlit_app.py --server.port %PORT%
endlocal
