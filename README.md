# 🛍️ EY CodeCrafters - AI-Powered E-Commerce Platform

[![React](https://img.shields.io/badge/React-19-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![Redis](https://img.shields.io/badge/Redis-Upstash-red.svg)](https://upstash.com/)
[![AI](https://img.shields.io/badge/AI-Groq%20Llama%203.1-purple.svg)](https://groq.com/)

> A modern, microservices-based e-commerce platform with AI-powered product recommendations, intelligent styling suggestions, and complete order lifecycle management.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Agent Details](#-agent-details)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Environment Variables](#-environment-variables)
- [Contributing](#-contributing)

---

## 🌟 Overview

EY CodeCrafters is a complete e-commerce solution featuring:

- **8 Microservice Agents** - Each handling specific business logic
- **AI-Powered Recommendations** - 3 intelligent modes (Normal, Gifting Genius, TrendSeer)
- **Real-Time Inventory** - Multi-store stock management across 5 locations
- **Smart Fulfillment** - Automated courier assignment and tracking
- **Post-Purchase Support** - Returns, exchanges, and AI styling tips
- **Loyalty System** - 4-tier rewards program (Bronze → Platinum)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                           │
│  React 19 + Vite + Tailwind CSS (Port 5173)                    │
│  - Chat Interface  - Kiosk Mode  - Responsive Design           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             v
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│  Sales Agent (Port 8000) - LangGraph + FastAPI                 │
│  - Intent Detection  - Conversation Flow  - Agent Routing      │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        v                                         v
┌─────────────────────┐              ┌─────────────────────┐
│  SHOPPING AGENTS    │              │  TRANSACTION AGENTS │
├─────────────────────┤              ├─────────────────────┤
│ Recommendation 8007 │              │ Inventory      8001 │
│ - Normal Mode       │              │ - Multi-store       │
│ - Gifting Genius    │              │ - Hold Management   │
│ - TrendSeer         │              │                     │
│                     │              │ Loyalty        8002 │
│ Stylist        8006 │              │ - Points System     │
│ - AI Styling Tips   │              │ - Tier Benefits     │
│ - Groq Llama 3.1    │              │                     │
│ - Outfit Combos     │              │ Payment        8003 │
└─────────────────────┘              │ - UPI/Card/Wallet   │
                                     │ - Refunds           │
                                     │                     │
                                     │ Fulfillment    8004 │
                                     │ - Shipping          │
                                     │ - Tracking          │
                                     │                     │
                                     │ Post-Purchase  8005 │
                                     │ - Returns           │
                                     │ - Exchanges         │
                                     └─────────────────────┘
```

### Data Flow

```
Customer Request → Sales Agent → Detect Intent
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                 ↓
             Recommendation      Inventory         Payment
                    ↓                 ↓                 ↓
              Show Products    Reserve Stock    Process Payment
                    ↓                 ↓                 ↓
                    └─────────────────┼─────────────────┘
                                      ↓
                                 Fulfillment
                                      ↓
                            Ship Order with Tracking
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                                   ↓
              Post-Purchase                        Stylist
              (Returns/Exchange)              (AI Recommendations)
```

---

## ✨ Features

### 🤖 AI-Powered Intelligence

#### 1. **Recommendation Agent** (3 Modes)
- **Normal Mode**: Personalized recommendations based on purchase history
- **Gifting Genius**: Smart gift suggestions based on recipient profile
- **TrendSeer**: Proactive trending product suggestions

#### 2. **AI Stylist Agent**
- Powered by **Groq Llama 3.1 70B**
- Analyzes purchased products
- Suggests matching outfits from real catalog
- Provides detailed styling tips

### 📦 Order Management

- **Multi-Store Inventory**: 5 physical stores + online warehouse
- **Smart Stock Holds**: 10-minute reservation with automatic release
- **Payment Gateway**: Support for UPI, Cards, Wallets, COD, Net Banking
- **Loyalty Integration**: Automatic tier-based discounts
- **Order Tracking**: Real-time status updates (PROCESSING → DELIVERED)

### 🎯 Post-Purchase Excellence

- **Easy Returns**: Quality/size/wrong item reasons
- **Quick Exchanges**: Size/color swaps
- **AI Styling Consultation**: "What to wear with this?"
- **Complaint Management**: Priority-based ticket system

---

## 🛠️ Tech Stack

### Frontend
- **React 19** - Latest React with modern hooks
- **Vite** - Lightning-fast build tool
- **Tailwind CSS** - Utility-first styling
- **React Router** - Client-side routing
- **Shadcn/ui** - Beautiful UI components

### Backend
- **FastAPI** - High-performance Python framework
- **Python 3.9+** - Core language
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **LangGraph** - Agent orchestration

### AI/ML
- **Groq API** - Llama 3.1 70B for styling recommendations
- **Pandas** - Data processing and analysis
- **NumPy** - Numerical computations

### Database & Storage
- **Redis (Upstash)** - Real-time data (holds, sessions, loyalty)
- **CSV Files** - Structured data (products, orders, inventory)

### DevOps
- **Git** - Version control
- **GitHub** - Repository hosting
- **Docker-ready** - Containerization support

---

## 🚀 Getting Started

### Prerequisites

```bash
# Check versions
python --version   # 3.9 or higher
node --version     # 18 or higher
npm --version      # 9 or higher
```

### Installation

#### 1. Clone Repository

```bash
git clone https://github.com/riddhij0804/EY_CodeCrafters.git
cd EY_CodeCrafters
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
REDIS_URL=rediss://default:YOUR_REDIS_PASSWORD@your-redis-host.upstash.io:6379
GROQ_API_KEY=gsk_YOUR_GROQ_API_KEY
EOF
```

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 🎮 Running the Application

### Start All Agents (Backend)

Open **8 separate terminals** and run each agent:

```bash
# Terminal 1 - Sales Agent (Port 8000)
cd backend/agents/sales_agent
python app.py

# Terminal 2 - Inventory Agent (Port 8001)
cd backend/agents/worker_agents/inventory
python app.py

# Terminal 3 - Loyalty Agent (Port 8002)
cd backend/agents/worker_agents/loyalty
python app.py

# Terminal 4 - Payment Agent (Port 8003)
cd backend/agents/worker_agents/payment
python app.py

# Terminal 5 - Fulfillment Agent (Port 8004)
cd backend/agents/worker_agents/fulfillment
python app.py

# Terminal 6 - Post-Purchase Agent (Port 8005)
cd backend/agents/worker_agents/post_purchase
python app.py

# Terminal 7 - Stylist Agent (Port 8006)
cd backend/agents/worker_agents/stylist
python app.py

# Terminal 8 - Recommendation Agent (Port 8007)
cd backend/agents/worker_agents/recommendation
python app.py
```

### Start Frontend

```bash
# Terminal 9
cd frontend
npm run dev
```

### Access Application

- **Frontend**: http://localhost:5173
- **Kiosk Mode**: http://localhost:5173/kiosk
- **Chat Interface**: http://localhost:5173/chat

---

## 🤖 Agent Details

### 1. Sales Agent (Port 8000)
**Orchestrator** - Routes customer requests to appropriate agents

**Endpoints:**
- `POST /chat` - Main conversation endpoint
- `POST /resume` - Resume existing session

**Capabilities:**
- Intent detection (shopping, tracking, returns, styling)
- Session management
- Multi-agent coordination

---

### 2. Recommendation Agent (Port 8007)
**Product Discovery** - Intelligent product suggestions

**Endpoints:**
- `POST /recommend` - Get personalized recommendations

**Request:**
```json
{
  "customer_id": "123",
  "mode": "normal",
  "intent": {
    "categories": ["Apparel"],
    "gender": "Men"
  },
  "cart_skus": ["SKU000123"],
  "limit": 5
}
```

**Modes:**
- `normal` - Personalized based on history
- `gifting_genius` - Gift recommendations
- `trendseer` - Trending products

---

### 3. Inventory Agent (Port 8001)
**Stock Management** - Multi-store inventory control

**Endpoints:**
- `POST /hold` - Reserve stock
- `POST /release` - Release hold
- `POST /check-availability` - Check stock

**Features:**
- 5 stores: Mumbai, Delhi, Bangalore, Chennai, Hyderabad
- Online inventory pooling
- 10-minute hold TTL
- Automatic expiration

---

### 4. Loyalty Agent (Port 8002)
**Rewards Program** - Points and tier management

**Endpoints:**
- `GET /loyalty/{user_id}` - Get loyalty status
- `POST /loyalty/earn` - Add points
- `POST /loyalty/redeem` - Use points

**Tiers:**
- Bronze: 0% discount (0-999 points)
- Silver: 5% discount (1000-4999 points)
- Gold: 10% discount (5000-9999 points)
- Platinum: 15% discount (10000+ points)

---

### 5. Payment Agent (Port 8003)
**Transaction Processing** - Secure payment handling

**Endpoints:**
- `POST /payment/process` - Process payment
- `POST /payment/refund` - Issue refund
- `GET /payment/{transaction_id}` - Get payment status

**Payment Methods:**
- UPI (Google Pay, PhonePe, Paytm)
- Credit/Debit Cards
- Net Banking
- Wallets (Paytm, Amazon Pay)
- Cash on Delivery (COD)

---

### 6. Fulfillment Agent (Port 8004)
**Order Shipping** - Logistics and tracking

**Endpoints:**
- `POST /fulfillment/start` - Start order processing
- `POST /fulfillment/update-status` - Update order status
- `GET /fulfillment/track/{order_id}` - Track order

**Status Flow:**
```
PROCESSING → PACKED → SHIPPED → OUT_FOR_DELIVERY → DELIVERED
```

**Couriers:**
- FedEx, DHL, UPS, Amazon Logistics, Local Courier

---

### 7. Post-Purchase Agent (Port 8005)
**Customer Support** - Returns and exchanges

**Endpoints:**
- `POST /post-purchase/return` - Initiate return
- `POST /post-purchase/exchange` - Request exchange
- `POST /post-purchase/complaint` - File complaint
- `GET /post-purchase/returns/{user_id}` - Get return history

**Return Reasons:**
- SIZE_ISSUE, QUALITY_ISSUE, WRONG_ITEM
- NOT_AS_DESCRIBED, CHANGED_MIND
- DAMAGED_IN_SHIPPING

---

### 8. Stylist Agent (Port 8006)
**AI Fashion Consultant** - Groq-powered styling

**Endpoints:**
- `POST /stylist/outfit-suggestions` - Get outfit recommendations
- `POST /stylist/care-instructions` - Product care tips
- `POST /stylist/occasion-styling` - Style for occasions
- `POST /stylist/seasonal-styling` - Seasonal fashion advice

**AI Features:**
- Analyzes purchased product
- Recommends 3-5 matching items from catalog
- Provides detailed styling tips
- Considers Indian fashion context

---

## 🧪 Testing

### Integration Test

Tests complete customer journey through all 5 core agents:

```bash
cd backend
python test_integration_workflow.py
```

**Test Flow:**
1. Load order from CSV
2. Reserve inventory → Get hold_id
3. Verify payment → Get transaction_id
4. Start fulfillment → Get tracking_id
5. Test return flow → Get return_id
6. Get AI styling recommendations

**Expected Output:**
```
✓ Complete Success (All 5 Agents): 5/5
✓ Inventory: Reserved
✓ Payment: Verified
✓ Fulfillment: Started
✓ Post-Purchase: Tested
✓ Stylist: 4 recommendations generated
```

### Individual Agent Tests

```bash
# Test Post-Purchase Agent
python test_post_purchase.py

# Test Stylist Agent
python test_stylist.py

# Test Loyalty + Payment
python test_loyalty_payment.py
```

---

## 📁 Project Structure

```
EY_CodeCrafters/
├── backend/
│   ├── .env                          # Environment variables
│   ├── requirements.txt              # Python dependencies
│   ├── test_integration_workflow.py  # E2E integration test
│   │
│   ├── agents/
│   │   ├── sales_agent/              # Port 8000 - Orchestrator
│   │   │   ├── app.py
│   │   │   ├── graph.ipynb           # LangGraph workflow
│   │   │   └── INTEGRATION_GUIDE.md
│   │   │
│   │   └── worker_agents/
│   │       ├── recommendation/       # Port 8007 - Product suggestions
│   │       │   ├── app.py
│   │       │   ├── 3_MODE_IMPLEMENTATION.md
│   │       │   └── SALES_AGENT_INTEGRATION.md
│   │       │
│   │       ├── inventory/            # Port 8001 - Stock management
│   │       │   ├── app.py
│   │       │   ├── redis_utils.py
│   │       │   └── README.md
│   │       │
│   │       ├── loyalty/              # Port 8002 - Rewards program
│   │       │   ├── app.py
│   │       │   └── seed_loyalty.py
│   │       │
│   │       ├── payment/              # Port 8003 - Transactions
│   │       │   ├── app.py
│   │       │   └── seed_payment.py
│   │       │
│   │       ├── fulfillment/          # Port 8004 - Shipping
│   │       │   ├── app.py
│   │       │   ├── INTEGRATION_GUIDE.md
│   │       │   └── README.md
│   │       │
│   │       ├── post_purchase/        # Port 8005 - Returns/Support
│   │       │   ├── app.py
│   │       │   └── redis_utils.py
│   │       │
│   │       └── stylist/              # Port 8006 - AI styling
│   │           ├── app.py
│   │           └── redis_utils.py
│   │
│   └── data/                         # CSV database
│       ├── products.csv              # 902 products
│       ├── orders.csv                # 909 orders
│       ├── inventory.csv             # 4510 inventory records
│       ├── customers.csv             # 350 customers
│       ├── payments.csv              # 1000 payments
│       └── stores.csv                # 5 store locations
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                   # Main app component
│   │   ├── main.jsx                  # Entry point
│   │   │
│   │   └── components/
│   │       ├── Chat.jsx              # Chat interface
│   │       ├── KioskChat.jsx         # Kiosk mode
│   │       └── ui/                   # Shadcn components
│   │           ├── button.jsx
│   │           └── card.jsx
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
└── README.md                         # This file
```

---

## 🔐 Environment Variables

Create `.env` file in `backend/` directory:

```env
# Redis Configuration (Upstash)
REDIS_URL=rediss://default:YOUR_PASSWORD@your-host.upstash.io:6379

# AI Configuration
GROQ_API_KEY=gsk_YOUR_GROQ_API_KEY_HERE

# Optional: Agent Ports (default values)
SALES_AGENT_PORT=8000
INVENTORY_AGENT_PORT=8001
LOYALTY_AGENT_PORT=8002
PAYMENT_AGENT_PORT=8003
FULFILLMENT_AGENT_PORT=8004
POST_PURCHASE_AGENT_PORT=8005
STYLIST_AGENT_PORT=8006
RECOMMENDATION_AGENT_PORT=8007
```

### Getting API Keys

1. **Redis (Upstash)**:
   - Sign up at https://upstash.com/
   - Create a Redis database
   - Copy the connection URL

2. **Groq API**:
   - Sign up at https://groq.com/
   - Navigate to API Keys section
   - Create new API key

---

## 📊 Data Model

### Products (products.csv)
```csv
sku,ProductDisplayName,brand,category,subcategory,price,ratings,attributes
SKU000001,Nike Running Shoes,Nike,Footwear,Shoes,2999.00,4.5,{"color":"Black","size":"[8,9,10]"}
```

### Orders (orders.csv)
```csv
order_id,customer_id,items,total_amount,status,order_date
ORD000001,123,[{"sku":"SKU000001","qty":1,"price":2999.00}],2999.00,delivered,2024-01-15
```

### Inventory (inventory.csv)
```csv
sku,store_id,quantity,last_updated
SKU000001,STORE_MUMBAI,150,2024-12-01
```

---

## 🎯 Use Cases

### 1. Personal Shopping
```
Customer: "I need running shoes for marathon training"
→ Recommendation Agent (Normal Mode)
→ Shows Nike/Adidas running shoes based on past purchases
→ Suggests matching activewear
```

### 2. Gift Shopping
```
Customer: "Gift for my wife, she likes dresses"
→ Recommendation Agent (Gifting Genius Mode)
→ Analyzes recipient profile
→ Suggests elegant dresses + jewelry
```

### 3. Trend Following
```
Customer: "What's trending this season?"
→ Recommendation Agent (TrendSeer Mode)
→ Shows popular items
→ Highlights fashion trends
```

### 4. Post-Purchase Styling
```
Customer: Buys white shirt
→ Order delivered
→ Stylist Agent recommends:
  - Dark blue jeans
  - Brown leather belt
  - Casual sneakers
→ Provides styling tips for office/casual/party wear
```

---

## 🔧 Configuration

### Adjust Recommendation Logic

Edit `backend/agents/worker_agents/recommendation/app.py`:

```python
# Change recommendation limit
DEFAULT_RECOMMENDATION_LIMIT = 5  # Change to 10 for more suggestions

# Adjust rating threshold
MIN_RATING_THRESHOLD = 4.0  # Only recommend 4+ star products

# Modify price range for upsell
UPSELL_PRICE_MULTIPLIER = 1.5  # Suggest items 50% more expensive
```

### Customize AI Styling

Edit `backend/agents/worker_agents/stylist/app.py`:

```python
# Change AI model
model="llama-3.1-70b-versatile"  # Switch to different Groq model

# Adjust creativity
temperature=0.7  # Higher = more creative (0.0 - 1.0)

# Modify prompt
prompt = """You are a fashion stylist..."""  # Customize AI behavior
```

---

## 🐛 Troubleshooting

### Agent Won't Start

```bash
# Check if port is already in use
netstat -ano | findstr "8001"  # Windows
lsof -i :8001                   # macOS/Linux

# Kill process on port
taskkill /PID <PID> /F          # Windows
kill -9 <PID>                   # macOS/Linux
```

### Redis Connection Error

```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check .env file exists
ls backend/.env

# Verify REDIS_URL format
rediss://default:PASSWORD@host.upstash.io:6379
```

### Import Errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check Python version
python --version  # Must be 3.9+

# Verify virtual environment is activated
which python      # Should point to venv
```

### AI Styling Not Working

```bash
# Verify Groq API key
echo $GROQ_API_KEY

# Test API directly
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY"

# Check agent logs for error details
```

---

## 📈 Performance Optimization

### Backend

1. **Enable Caching**:
   ```python
   # Cache product catalog in memory
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def get_product_details(sku):
       return products_df[products_df['sku'] == sku]
   ```

2. **Use Connection Pooling**:
   ```python
   # Redis connection pool
   redis_client = redis.ConnectionPool(
       max_connections=20,
       decode_responses=True
   )
   ```

3. **Async Operations**:
   ```python
   # Use async for I/O operations
   async def process_order(order_id):
       inventory, payment = await asyncio.gather(
           reserve_inventory(order_id),
           process_payment(order_id)
       )
   ```

### Frontend

1. **Code Splitting**:
   ```jsx
   const Chat = lazy(() => import('./components/Chat'));
   ```

2. **Memoization**:
   ```jsx
   const MemoizedProductCard = React.memo(ProductCard);
   ```

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Cloud Deployment (Azure/AWS)

1. Deploy each agent as separate container
2. Use Azure App Service / AWS ECS
3. Configure environment variables
4. Set up load balancer
5. Enable auto-scaling

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Code Style

- **Python**: Follow PEP 8
- **JavaScript**: Use ESLint configuration
- **Commit Messages**: Use conventional commits

---

## 📝 License

This project is proprietary and confidential. © 2025 EY CodeCrafters Team

---

## 👥 Team

- **Backend Architecture**: Multi-agent microservices
- **AI Integration**: Groq Llama 3.1 70B
- **Frontend**: React 19 + Vite
- **DevOps**: Redis, FastAPI, Git

---

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Contact: ey.codecrafters@example.com

---

## 🎉 Acknowledgments

- **Groq** - Lightning-fast AI inference
- **Upstash** - Serverless Redis
- **FastAPI** - Modern Python framework
- **React Team** - Awesome frontend library
- **EY** - Project support

---

<div align="center">

**Built with ❤️ by EY CodeCrafters Team**

[Demo](http://localhost:5173) • [Documentation](./backend/agents/) • [Report Bug](https://github.com/riddhij0804/EY_CodeCrafters/issues)

</div>
