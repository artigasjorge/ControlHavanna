@echo off
cd /d "%~dp0"
echo Iniciando ControlHavanna...
echo.
streamlit run app.py
echo.
echo La aplicacion se cerro o no pudo iniciarse.
pause
