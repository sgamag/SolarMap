@echo off
title SolarMap - Arranque completo

echo ===============================
echo      INICIANDO SOLARMAP
echo ===============================

REM -------------------------------
REM BACKEND FASTAPI + MODELO
REM -------------------------------

start "Backend FastAPI - Modelo IA" cmd /k "cd /d C:\BigData1\PROYECTOBIGDATA && .venv\Scripts\activate && cd /d C:\BigData1\PROYECTOBIGDATA\src\Mapa y Modelo Tejados && uvicorn api.main:app --reload"

REM -------------------------------
REM FRONTEND REACT
REM -------------------------------

start "Frontend React - SolarMap" cmd /k "cd /d C:\BigData1\PROYECTOBIGDATA\frontend\solarmapuem-main && npm run dev"

REM -------------------------------
REM ESPERAR Y ABRIR WEB
REM -------------------------------

timeout /t 6 > nul

start http://localhost:8080

echo.
echo SolarMap iniciado correctamente.
echo No cierres las terminales abiertas.
echo.

pause