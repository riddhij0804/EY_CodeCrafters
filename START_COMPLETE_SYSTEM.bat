@echo off
REM Complete System Startup Script
REM Starts all backend services and frontend

echo ========================================
echo Starting Complete EY CodeCrafters System
echo ========================================
echo.

echo Step 1: Starting Backend Services...
echo ----------------------------------------
start "Backend Services" cmd /k "cd backend && python start_all_services.py"

echo Waiting for services to start...
timeout /t 5 /nobreak > nul

echo.
echo Step 2: Starting Frontend...
echo ----------------------------------------
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo All services starting!
echo ========================================
echo.
echo Backend Services Running:
echo - Session Manager:     http://localhost:8000
echo - Inventory Agent:     http://localhost:8001
echo - Loyalty Agent:       http://localhost:8002
echo - Payment Agent:       http://localhost:8003
echo - Fulfillment Agent:   http://localhost:8004
echo - Post-Purchase Agent: http://localhost:8005
echo - Stylist Agent:       http://localhost:8006
echo - Data API:            http://localhost:8007
echo - Recommendation:      http://localhost:8008
echo - Ambient Commerce:    http://localhost:8009
echo - Sales Agent:         http://localhost:8010
echo.
echo Frontend:              http://localhost:5173
echo.
echo Press any key to exit...
pause > nul
