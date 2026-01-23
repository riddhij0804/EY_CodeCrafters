# 🚀 QUICK START GUIDE

## Run Everything in 3 Commands:

### 1. Start Backend (2 terminals needed):

**Terminal 1 - Session Manager:**
```powershell
cd backend
python -m uvicorn session_manager:app --port 8000 --reload
```

**Terminal 2 - Sales Agent:**
```powershell
cd backend\agents\sales_agent
python -m uvicorn app:app --port 8001 --reload
```

### 2. Start Frontend:
```powershell
cd frontend
npm run dev
```

### 3. Test in Browser:
- Open: http://localhost:5173
- Try Chat or Kiosk
- Ask: "suggest gifts for girl"

---

## ✅ What's Working:

### Session Manager (Port 8000):
- ✅ Phone-based sessions
- ✅ Chat history storage
- ✅ Multi-channel (WhatsApp/Kiosk)

### Sales Agent (Port 8001):
- ✅ Loads 900+ products from CSV
- ✅ Loads 4500+ inventory records
- ✅ Real product search
- ✅ Gift recommendations
- ✅ Stock availability

### Frontend:
- ✅ Chat interface with voice
- ✅ Kiosk interface
- ✅ Real product data display
- ✅ Session persistence

---

## 🧪 Test Queries:

1. **Gift Search:**
   - "suggest gifts for my bestfriend she is a girl"
   - Shows: Real products with prices & stock

2. **Product Search:**
   - "show me Nike shoes"
   - "what Reebok products do you have"

3. **Order Tracking:**
   - "track my order ORD-123"

---

## 📊 Expected Console Output:

**Session Manager:**
```
✅ Session Manager running on http://localhost:8000
```

**Sales Agent:**
```
✅ Loaded 903 products and 4512 inventory records
Sample product: Men Black Possession Flip Flops
✅ Sales Agent running on http://localhost:8001
```

**Frontend:**
```
VITE ready in 500ms
Local: http://localhost:5173
```

---

## ⚡ Quick Commands:

```powershell
# Kill all Python processes if needed
Get-Process python | Stop-Process -Force

# Or use the batch file:
start_backend.bat
```

**Everything is configured and ready to run!** 🎉
