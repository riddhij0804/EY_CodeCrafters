@echo off
echo ========================================
echo  STARTING ALL AGENTS - EY CodeCrafters
echo ========================================

echo.
echo [1/11] Starting Session Manager on port 8000...
start "Session Manager" cmd /k "cd backend && python -m uvicorn session_manager:app --port 8000 --reload"
timeout /t 2

echo.
echo [2/11] Starting Sales Agent on port 8001...
start "Sales Agent" cmd /k "cd backend\agents\sales_agent && python -m uvicorn app:app --port 8001 --reload"
timeout /t 2

echo.
echo [3/11] Starting Inventory Agent on port 8002...
start "Inventory Agent" cmd /k "cd backend\agents\worker_agents\inventory && python -m uvicorn app:app --port 8002 --reload"
timeout /t 2

echo.
echo [4/11] Starting Payment Agent on port 8003...
start "Payment Agent" cmd /k "cd backend\agents\worker_agents\payment && python -m uvicorn app:app --port 8003 --reload"
timeout /t 2

echo.
echo [5/11] Starting Loyalty Agent on port 8004...
start "Loyalty Agent" cmd /k "cd backend\agents\worker_agents\loyalty && python -m uvicorn app:app --port 8004 --reload"
timeout /t 2

echo.
echo [6/11] Starting Virtual Circles Agent on port 8005...
start "Virtual Circles" cmd /k "cd backend\agents\worker_agents\virtual_circles && python -m uvicorn app:app --port 8005 --reload"
timeout /t 2

echo.
echo [7/11] Starting Fulfillment Agent on port 8006...
start "Fulfillment Agent" cmd /k "cd backend\agents\worker_agents\fulfillment && python -m uvicorn app:app --port 8006 --reload"
timeout /t 2

echo.
echo [8/11] Starting Post-Purchase Agent on port 8007...
start "Post-Purchase" cmd /k "cd backend\agents\worker_agents\post_purchase && python -m uvicorn app:app --port 8007 --reload"
timeout /t 2

echo.
echo [9/11] Starting Recommendation Agent on port 8008...
start "Recommendation" cmd /k "cd backend\agents\worker_agents\recommendation && python -m uvicorn app:app --port 8008 --reload"
timeout /t 2

echo.
echo [10/11] Starting Stylist Agent on port 8009...
start "Stylist Agent" cmd /k "cd backend\agents\worker_agents\stylist && python -m uvicorn app:app --port 8009 --reload"
timeout /t 2

echo.
echo [11/11] Starting Ambient Commerce Agent on port 8010...
start "Ambient Commerce" cmd /k "cd backend\agents\worker_agents\ambient_commerce && python -m uvicorn app:app --port 8010 --reload"
timeout /t 3

echo.
echo ========================================
echo ALL AGENTS STARTED SUCCESSFULLY!
echo ========================================
echo.
echo Running Services:
echo - Session Manager:     http://localhost:8000
echo - Sales Agent:         http://localhost:8001
echo - Inventory:           http://localhost:8002
echo - Payment:             http://localhost:8003
echo - Loyalty:             http://localhost:8004
echo - Virtual Circles:     http://localhost:8005
echo - Fulfillment:         http://localhost:8006
echo - Post-Purchase:       http://localhost:8007
echo - Recommendation:      http://localhost:8008
echo - Stylist:             http://localhost:8009
echo - Ambient Commerce:    http://localhost:8010
echo.
echo Now starting Frontend...
timeout /t 3
start "Frontend" cmd /k "cd frontend && npm run dev"
echo.
echo ========================================
echo Frontend: http://localhost:3000
echo ========================================
pause
