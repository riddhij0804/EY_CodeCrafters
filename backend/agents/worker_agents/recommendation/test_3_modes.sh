#!/bin/bash
# Test script for 3-Mode Recommendation Agent

echo "================================================"
echo "🧪 Testing 3-Mode Recommendation Agent"
echo "================================================"

echo ""
echo "1️⃣  MODE 1: NORMAL RECOMMENDATION"
echo "   Scenario: Customer 104 wants casual footwear under 5000"
echo "------------------------------------------------"
curl -X POST http://localhost:8004/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "104",
    "mode": "normal",
    "intent": {
      "category": "Footwear",
      "occasion": "casual",
      "budget_max": 5000
    },
    "limit": 3
  }' | python3 -m json.tool

echo ""
echo ""
echo "2️⃣  MODE 2: GIFTING GENIUS"
echo "   Scenario: Male customer buying birthday gift for wife"
echo "------------------------------------------------"
curl -X POST http://localhost:8004/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "104",
    "mode": "gifting_genius",
    "recipient_relation": "wife",
    "recipient_gender": "Female",
    "age_range": "25-35",
    "interests": ["blue", "elegant"],
    "occasion": "birthday",
    "intent": {
      "budget_min": 2000,
      "budget_max": 4000
    },
    "preferred_brands": ["Allen Solly", "Van Heusen"],
    "safe_sizes_only": true,
    "limit": 3
  }' | python3 -m json.tool

echo ""
echo ""
echo "3️⃣  MODE 3: TRENDSEER (Predictive AI)"
echo "   Scenario: Predict what customer 104 will need next"
echo "------------------------------------------------"
curl -X POST http://localhost:8004/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "104",
    "mode": "trendseer",
    "limit": 5
  }' | python3 -m json.tool

echo ""
echo "================================================"
echo "✅ All 3 modes tested!"
echo "================================================"
