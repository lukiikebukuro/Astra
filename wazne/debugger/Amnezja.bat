@echo off
REM ============================================
REM   AMNEZJA - RAG Debugger (launcher)
REM   Otwiera narzedzie w przegladarce.
REM   Wymaga: deploy galezi na VPS + Basic Auth (login/haslo).
REM ============================================
title Amnezja - RAG Debugger
echo.
echo   Otwieram Amnezje...
echo   (jesli poprosi o login/haslo - to Basic Auth)
echo.
start "" "https://myastra.pl/amnezja"
timeout /t 2 >nul
