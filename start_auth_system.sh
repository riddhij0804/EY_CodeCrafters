#!/bin/bash

# 🚀 Quick Start Script for Authentication System
# This script helps you start the system and verify everything is working

echo "════════════════════════════════════════════════════════════"
echo "  🔐 EY CodeCrafters - Authentication System Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Error: Please run this script from the EY_CodeCrafters root directory${NC}"
    exit 1
fi

print_section "Step 1: Installing Backend Dependencies"
cd backend
echo "Installing bcrypt and pandas..."
pip install bcrypt pandas
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install backend dependencies${NC}"
    exit 1
fi
cd ..

print_section "Step 2: Checking Frontend Dependencies"
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
    else
        echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Frontend dependencies already installed${NC}"
fi
cd ..

print_section "Step 3: Verifying Auth Manager"
cd backend
python -c "import auth_manager; print('Auth manager verification complete')" 2>&1 | grep -q "Created default passwords"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Auth manager loaded successfully${NC}"
    echo -e "${GREEN}✅ Default passwords created for existing customers${NC}"
    echo -e "${YELLOW}📌 Default Password: Reebok@123${NC}"
else
    echo -e "${YELLOW}⚠️  Auth manager loaded (check logs for details)${NC}"
fi
cd ..

print_section "Step 4: Starting Services"
echo "This script will help you start the backend and frontend services."
echo ""
echo "You need to run these commands in SEPARATE terminal windows:"
echo ""
echo -e "${YELLOW}Terminal 1 (Backend):${NC}"
echo "  cd backend"
echo "  python session_manager.py"
echo ""
echo -e "${YELLOW}Terminal 2 (Frontend):${NC}"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo -e "${BLUE}Would you like to see detailed startup instructions? (y/n)${NC}"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    print_section "Detailed Startup Instructions"
    
    echo -e "${YELLOW}1. Start Backend Session Manager:${NC}"
    echo "   Open a NEW terminal window and run:"
    echo "   $ cd $(pwd)/backend"
    echo "   $ python session_manager.py"
    echo ""
    echo "   Expected output:"
    echo "   ✅ Created default passwords for XXX existing customers"
    echo "   📌 Default password: 'Reebok@123'"
    echo "   🔐 Auth manager initialized successfully"
    echo "   INFO: Uvicorn running on http://0.0.0.0:8000"
    echo ""
    
    echo -e "${YELLOW}2. Start Frontend Dev Server:${NC}"
    echo "   Open ANOTHER terminal window and run:"
    echo "   $ cd $(pwd)/frontend"
    echo "   $ npm run dev"
    echo ""
    echo "   Expected output:"
    echo "   VITE v5.x.x ready in XXX ms"
    echo "   ➜ Local: http://localhost:5173/"
    echo ""
    
    echo -e "${YELLOW}3. Open Browser:${NC}"
    echo "   Visit: http://localhost:5173"
    echo ""
    
    echo -e "${YELLOW}4. Test Login:${NC}"
    echo "   Look for 'LOGIN / SIGNUP' button in the top-right navbar"
    echo "   Click it and try logging in with:"
    echo "   - Phone: 9000000000"
    echo "   - Password: Reebok@123"
    echo ""
    
    echo -e "${YELLOW}5. Verify Navbar Changes:${NC}"
    echo "   After login, you should see:"
    echo "   - Your name button (with dropdown)"
    echo "   - 'PROFILE' button"
    echo "   - 'LOGOUT' button"
    echo ""
fi

print_section "Step 5: Testing the System"
echo "After starting both services, you can run the test suite:"
echo ""
echo "  $ cd backend"
echo "  $ python test_auth_system.py"
echo ""
echo "This will test all authentication flows."

print_section "Quick Reference"
echo -e "${GREEN}✅ Existing Customer Login:${NC}"
echo "   Phone: 9000000000"
echo "   Password: Reebok@123"
echo ""
echo -e "${GREEN}✅ New User Signup:${NC}"
echo "   Visit: http://localhost:5173/login"
echo "   Click: 'Don't have an account? Sign up'"
echo "   Create account with custom password"
echo ""
echo -e "${GREEN}✅ Navbar Features:${NC}"
echo "   - LOGIN/SIGNUP button (when not logged in)"
echo "   - User name, PROFILE, LOGOUT (when logged in)"
echo "   - Cart and Wishlist icons"
echo ""

print_section "Documentation"
echo "📄 AUTH_IMPLEMENTATION.md  - Full implementation details"
echo "📄 CREDENTIALS.md          - Login credentials guide"
echo "🧪 test_auth_system.py     - Automated test suite"
echo ""

print_section "Summary"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Start backend:  cd backend && python session_manager.py"
echo "2. Start frontend: cd frontend && npm run dev"
echo "3. Open browser:   http://localhost:5173"
echo "4. Look for the LOGIN/SIGNUP button in navbar!"
echo ""
echo -e "${YELLOW}Default password for existing customers: Reebok@123${NC}"
echo ""
echo "════════════════════════════════════════════════════════════"

