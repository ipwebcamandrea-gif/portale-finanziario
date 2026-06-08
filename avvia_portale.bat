@echo off
title Avvio Portale TradingView Streamlit
echo ===================================================
echo   Inizializzazione dell'ambiente tramite Python...
echo ===================================================
cd /d C:\portale_finanziario

echo Avvio del modulo Streamlit con Python...
python -m streamlit run main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRORE] Riscontrato un problema durante l'esecuzione di Python/Streamlit.
    pause
)