@echo off
echo ================================
echo STARTING ALL SERVICES
echo ================================

echo.
echo [1/2] Starting Session Manager on port 8000...
start "Session Manager" cmd /k "cd backend && python -m uvicorn session_manager:app --port 8000 --reload"
timeout /t 3

echo.
echo [2/2] Starting Sales Agent on port 8001...
start "Sales Agent" cmd /k "cd backend\agents\sales_agent && python -m uvicorn app:app --port 8001 --reload"
timeout /t 3

echo.
echo ================================
echo SERVICES STARTED!
echo ================================
echo Session Manager: http://localhost:8000
echo Sales Agent: http://localhost:8001
echo.
echo Now run: cd frontend && npm run dev
echo ================================
pause
