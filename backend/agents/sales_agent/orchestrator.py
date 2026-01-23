"""
Sales Agent Orchestrator - Coordinates Sales Agent with all Worker Agents
Implements the complete workflow from the proposed solution:
1. Discovery & Browsing Context
2. Visual Search (Ambient Commerce)
3. Profile-based Recommendations
4. Gifting Suggestions
5. Inventory Verification
6. Payment Processing
7. Post-Purchase Styling
8. Fulfillment Tracking
9. Returns/Exchanges
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pathlib import Path
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
SERVICES = {
    "inventory": "http://localhost:8001",
    "loyalty": "http://localhost:8002",
    "payment": "http://localhost:8003",
    "fulfillment": "http://localhost:8004",
    "post_purchase": "http://localhost:8005",
    "stylist": "http://localhost:8006",
    "recommendation": "http://localhost:8008",
    "ambient_commerce": "http://localhost:8009",
    "data_api": "http://localhost:8007",
}

# Load CSV data for context
# Path: orchestrator.py -> sales_agent/ -> agents/ -> backend/ -> data/
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


class SalesOrchestrator:
    """Orchestrates sales workflow across all agents"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=3.0)  # Short timeout to prevent hanging
        self.products_df = None
        self.customers_df = None
        self.load_data()
    
    def load_data(self):
        """Load CSV data"""
        try:
            products_path = DATA_DIR / "products.csv"
            customers_path = DATA_DIR / "customers.csv"
            
            logger.info(f"Loading data from: {DATA_DIR}")
            logger.info(f"Products CSV: {products_path}")
            logger.info(f"Products CSV exists: {products_path.exists()}")
            
            if not products_path.exists():
                logger.error(f"❌ Products CSV not found at: {products_path}")
                logger.error(f"Current working directory: {Path.cwd()}")
                return
            
            self.products_df = pd.read_csv(products_path)
            self.customers_df = pd.read_csv(customers_path)
            logger.info(f"✅ Loaded {len(self.products_df)} products and {len(self.customers_df)} customers")
            
            # Log sample data
            if len(self.products_df) > 0:
                logger.info(f"Sample product: {self.products_df.iloc[0]['ProductDisplayName']}")
                logger.info(f"Categories available: {self.products_df['category'].unique().tolist()}")
            
        except Exception as e:
            logger.error(f"❌ Error loading data: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def analyze_intent(self, message: str, user_profile: Dict) -> Dict[str, Any]:
        """
        Step 1: Analyze customer intent and browsing context
        Based on: "The system analyzes her preferences and browsing context"
        """
        msg_lower = message.lower()
        
        intent = {
            "is_shopping": any(word in msg_lower for word in ["buy", "shop", "looking for", "need", "want", "suggest", "show me", "find", "get"]),
            "is_browsing": any(word in msg_lower for word in ["show", "browse", "look", "see"]),
            "is_gifting": any(word in msg_lower for word in ["gift", "present", "birthday", "anniversary", "for my", "for his", "for her", "for someone"]),
            "occasion": None,
            "style_preference": user_profile.get("style_preference", "casual"),
            "budget": user_profile.get("budget", "mid"),
            "product_type": None,
            "search_query": message,
            "max_price": None
        }
        
        # Extract price/budget constraints
        import re
        price_patterns = [
            r'under\s+(\d+)',
            r'below\s+(\d+)',
            r'less than\s+(\d+)',
            r'max\s+(\d+)',
            r'budget\s+(\d+)',
            r'around\s+(\d+)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                try:
                    intent["max_price"] = int(match.group(1))
                    break
                except:
                    pass
        
        # Detect occasion
        if "weekend" in msg_lower or "trip" in msg_lower:
            intent["occasion"] = "weekend_trip"
        elif "office" in msg_lower or "work" in msg_lower:
            intent["occasion"] = "office"
        elif "party" in msg_lower or "event" in msg_lower:
            intent["occasion"] = "party"
        
        # Detect product type
        if any(word in msg_lower for word in ["shoe", "shoes", "footwear", "sneaker", "boot", "sandal", "slipper"]):
            intent["product_type"] = "footwear"
            if any(word in msg_lower for word in ["sport", "sporty", "athletic", "running", "training"]):
                intent["style_preference"] = "sports"
            if any(word in msg_lower for word in ["brand", "branded"]):
                intent["style_preference"] = "branded"
        elif any(word in msg_lower for word in ["shirt", "tshirt", "t-shirt", "top"]):
            intent["product_type"] = "apparel"
        elif any(word in msg_lower for word in ["jacket", "coat"]):
            intent["product_type"] = "apparel"
        
        # If no specific product type but user is shopping, mark as general shopping
        if not intent["product_type"] and intent["is_shopping"]:
            intent["is_general_shopping"] = True
        
        return intent
    
    async def get_recommendations(self, user_id: str, intent: Dict, context: Dict) -> List[Dict]:
        """
        Step 2: Get personalized recommendations
        Based on: "Present curated outfit styles that match her intent"
        """
        # Use fallback immediately for speed - can be enhanced later
        logger.info("Using CSV-based recommendations for fast response")
        return self._fallback_recommendations(intent)
    
    def _fallback_recommendations(self, intent: Dict) -> List[Dict]:
        """Fallback recommendations from CSV - fast and reliable"""
        try:
            if self.products_df is None or len(self.products_df) == 0:
                logger.warning("No products data available")
                return []
            
            filtered = self.products_df.copy()
            
            # Filter by product type
            if intent.get("product_type") == "footwear":
                filtered = filtered[filtered['category'].str.lower() == 'footwear']
            elif intent.get("product_type") == "apparel":
                filtered = filtered[filtered['category'].str.lower() == 'apparel']
            
            # Filter by price
            max_price = intent.get("max_price")
            if max_price:
                filtered = filtered[filtered['price'] <= max_price]
            
            # Filter by search keywords from query
            search_query = intent.get("search_query", "").lower()
            if search_query:
                # Broader keyword matching
                keywords = ["sport", "sporty", "athletic", "running", "training", "shoe", "sneaker", 
                           "nike", "adidas", "puma", "reebok", "brand"]
                matching_keywords = [kw for kw in keywords if kw in search_query]
                
                if matching_keywords:
                    # Filter products that contain any of the keywords in name or brand
                    try:
                        name_mask = filtered['ProductDisplayName'].str.lower().str.contains('|'.join(matching_keywords), na=False)
                        brand_mask = False
                        if 'brand' in filtered.columns:
                            brand_mask = filtered['brand'].str.lower().str.contains('|'.join(matching_keywords), na=False)
                        
                        combined_mask = name_mask | brand_mask if isinstance(brand_mask, type(name_mask)) else name_mask
                        if combined_mask.any():
                            filtered = filtered[combined_mask]
                    except Exception as e:
                        logger.warning(f"Error in keyword filtering: {e}")
            
            # If no products found after filtering, relax constraints
            if len(filtered) == 0:
                filtered = self.products_df.copy()
                if intent.get("product_type") == "footwear":
                    filtered = filtered[filtered['category'].str.lower() == 'footwear']
                if max_price:
                    filtered = filtered[filtered['price'] <= max_price]
            
            # Sort by price (ascending) to show cheaper options first
            if len(filtered) > 0:
                filtered = filtered.sort_values('price')
            
            # Sample products
            sample_size = min(5, len(filtered))
            if sample_size > 0:
                recommendations = filtered.head(sample_size).to_dict('records')
                logger.info(f"Returning {len(recommendations)} recommendations")
                return recommendations
            
            logger.warning("No products matched the criteria")
            return []
            
        except Exception as e:
            logger.error(f"Error in fallback recommendations: {e}")
            return []
    
    async def visual_search(self, image_path: str) -> List[Dict]:
        """
        Step 3: Visual search for similar products
        Based on: "System identifies visually similar product from catalog"
        """
        try:
            # Call ambient commerce agent for visual search
            response = await self.client.post(
                f"{SERVICES['ambient_commerce']}/search/image",
                files={"image": open(image_path, "rb")},
                data={"top_k": 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                logger.warning(f"Visual search returned {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error in visual search: {e}")
            return []
    
    async def get_profile_based_recommendations(self, user_id: str) -> List[Dict]:
        """
        Step 4: Profile-based recommendations
        Based on: "By comparing profile with similar shoppers, recommend commonly bought items"
        """
        try:
            response = await self.client.post(
                f"{SERVICES['recommendation']}/recommend/similar-users",
                json={"user_id": user_id, "limit": 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("recommendations", [])
                
        except Exception as e:
            logger.error(f"Error getting profile recommendations: {e}")
            return []
    
    async def get_gifting_suggestions(self, recipient_profile: Dict, user_preferences: Dict) -> List[Dict]:
        """
        Step 5: Tailored gift suggestions
        Based on: "System creates tailored gift suggestions based on recipient interests"
        """
        try:
            response = await self.client.post(
                f"{SERVICES['recommendation']}/recommend/gifts",
                json={
                    "recipient_interests": recipient_profile.get("interests", []),
                    "recipient_age": recipient_profile.get("age"),
                    "recipient_gender": recipient_profile.get("gender"),
                    "budget": user_preferences.get("budget"),
                    "occasion": user_preferences.get("occasion")
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("recommendations", [])
                
        except Exception as e:
            logger.error(f"Error getting gift suggestions: {e}")
            return []
    
    async def verify_inventory(self, items: List[Dict]) -> Dict[str, Any]:
        """
        Step 6: Verify inventory and check stock levels
        Based on: "Before checkout, all items verified for availability with low-stock alerts"
        """
        verification_results = {
            "all_available": True,
            "items": [],
            "low_stock_alerts": []
        }
        
        for item in items:
            try:
                sku = item.get("sku")
                quantity = item.get("quantity", 1)
                
                # Check inventory
                response = await self.client.get(f"{SERVICES['inventory']}/inventory/{sku}")
                
                if response.status_code == 200:
                    inventory_data = response.json()
                    total_stock = inventory_data.get("total_stock", 0)
                    
                    item_status = {
                        "sku": sku,
                        "requested_quantity": quantity,
                        "available_stock": total_stock,
                        "is_available": total_stock >= quantity,
                        "is_low_stock": 0 < total_stock < 5
                    }
                    
                    verification_results["items"].append(item_status)
                    
                    if not item_status["is_available"]:
                        verification_results["all_available"] = False
                    
                    if item_status["is_low_stock"]:
                        verification_results["low_stock_alerts"].append({
                            "sku": sku,
                            "stock": total_stock,
                            "message": f"Only {total_stock} items left in stock!"
                        })
                        
            except Exception as e:
                logger.error(f"Error checking inventory for {item.get('sku')}: {e}")
                verification_results["all_available"] = False
        
        return verification_results
    
    async def create_inventory_holds(self, items: List[Dict], session_id: str) -> List[Dict]:
        """Create inventory holds for items before payment"""
        holds = []
        
        for item in items:
            try:
                response = await self.client.post(
                    f"{SERVICES['inventory']}/hold",
                    json={
                        "sku": item["sku"],
                        "quantity": item.get("quantity", 1),
                        "location": "online",
                        "ttl": 600  # 10 minutes
                    },
                    headers={"X-Idempotency-Key": f"{session_id}-{item['sku']}"}
                )
                
                if response.status_code == 200:
                    hold_data = response.json()
                    holds.append(hold_data)
                    
            except Exception as e:
                logger.error(f"Error creating hold for {item['sku']}: {e}")
        
        return holds
    
    async def process_payment(self, customer_id: str, order_total: float, payment_method: Dict) -> Dict:
        """
        Step 7: Process payment
        Based on: "Payment Agent completes checkout - secure payment flow"
        """
        try:
            response = await self.client.post(
                f"{SERVICES['payment']}/payment/process",
                json={
                    "customer_id": customer_id,
                    "amount": order_total,
                    "payment_method": payment_method,
                    "currency": "INR"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "failed", "error": "Payment processing failed"}
                
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def get_styling_suggestions(self, purchased_items: List[Dict], customer_id: str) -> List[Dict]:
        """
        Step 8: Post-purchase styling suggestions
        Based on: "Shortly after purchase, system shares styling ideas"
        """
        styling_suggestions = []
        
        for item in purchased_items:
            try:
                response = await self.client.post(
                    f"{SERVICES['stylist']}/stylist/outfit-suggestions",
                    json={
                        "user_id": customer_id,
                        "product_sku": item["sku"],
                        "product_name": item.get("name", ""),
                        "category": item.get("category", ""),
                        "color": item.get("color"),
                        "brand": item.get("brand")
                    }
                )
                
                if response.status_code == 200:
                    suggestions = response.json()
                    styling_suggestions.append(suggestions)
                    
            except Exception as e:
                logger.error(f"Error getting styling suggestions: {e}")
        
        return styling_suggestions
    
    async def start_fulfillment(self, order_id: str, customer_id: str, items: List[Dict], shipping_address: Dict) -> Dict:
        """
        Step 9: Start fulfillment process
        Based on: "Fulfillment Agent handles shipping - order packed, shipped, tracked"
        """
        try:
            response = await self.client.post(
                f"{SERVICES['fulfillment']}/fulfillment/start",
                json={
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "items": items,
                    "shipping_address": shipping_address,
                    "shipping_method": "standard"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "failed", "error": "Fulfillment failed"}
                
        except Exception as e:
            logger.error(f"Error starting fulfillment: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def handle_return_exchange(self, order_id: str, items: List[Dict], reason: str, action: str) -> Dict:
        """
        Step 10: Handle returns/exchanges
        Based on: "Post-Purchase Agent manages returns/exchanges"
        """
        try:
            response = await self.client.post(
                f"{SERVICES['post_purchase']}/post-purchase/return",
                json={
                    "order_id": order_id,
                    "items": items,
                    "reason": reason,
                    "action": action  # "return" or "exchange"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "failed", "error": "Return/exchange failed"}
                
        except Exception as e:
            logger.error(f"Error handling return/exchange: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def get_seasonal_trends(self, season: str = None) -> List[Dict]:
        """
        Get seasonal trends for proactive recommendations
        Based on: "System proactively highlights current seasonal trends"
        """
        if season is None:
            # Detect current season
            month = datetime.now().month
            if month in [12, 1, 2]:
                season = "winter"
            elif month in [3, 4, 5]:
                season = "spring"
            elif month in [6, 7, 8]:
                season = "summer"
            else:
                season = "fall"
        
        # Get trending products for the season
        if self.products_df is not None:
            # Filter by season-appropriate categories
            seasonal_keywords = {
                "winter": ["jacket", "sweater", "coat", "thermal"],
                "summer": ["shirt", "shorts", "sandal", "tee"],
                "spring": ["light", "casual", "sneaker"],
                "fall": ["jacket", "boot", "layer"]
            }
            
            keywords = seasonal_keywords.get(season, [])
            if keywords:
                filtered = self.products_df[
                    self.products_df['ProductDisplayName'].str.lower().str.contains('|'.join(keywords), na=False)
                ]
                
                if len(filtered) > 0:
                    trends = filtered.sample(n=min(10, len(filtered))).to_dict('records')
                    return trends
        
        return []
    
    async def complete_purchase_flow(self, customer_id: str, items: List[Dict], 
                                    payment_method: Dict, shipping_address: Dict) -> Dict:
        """
        Complete end-to-end purchase flow
        Orchestrates: Inventory Check -> Hold -> Payment -> Fulfillment -> Post-Purchase
        """
        flow_result = {
            "status": "initiated",
            "steps": {},
            "order_id": f"ORD-{datetime.now().strftime('%Y%m%d')}-{customer_id[:8]}"
        }
        
        try:
            # Step 1: Verify inventory
            logger.info("Step 1: Verifying inventory...")
            inventory_check = await self.verify_inventory(items)
            flow_result["steps"]["inventory_check"] = inventory_check
            
            if not inventory_check["all_available"]:
                flow_result["status"] = "failed"
                flow_result["error"] = "Some items are out of stock"
                return flow_result
            
            # Step 2: Create inventory holds
            logger.info("Step 2: Creating inventory holds...")
            holds = await self.create_inventory_holds(items, flow_result["order_id"])
            flow_result["steps"]["holds"] = holds
            
            # Step 3: Calculate order total
            order_total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
            flow_result["order_total"] = order_total
            
            # Step 4: Process payment
            logger.info("Step 3: Processing payment...")
            payment_result = await self.process_payment(customer_id, order_total, payment_method)
            flow_result["steps"]["payment"] = payment_result
            
            if payment_result.get("status") != "success":
                flow_result["status"] = "payment_failed"
                return flow_result
            
            # Step 5: Start fulfillment
            logger.info("Step 4: Starting fulfillment...")
            fulfillment_result = await self.start_fulfillment(
                flow_result["order_id"], customer_id, items, shipping_address
            )
            flow_result["steps"]["fulfillment"] = fulfillment_result
            
            # Step 6: Get post-purchase styling suggestions
            logger.info("Step 5: Getting styling suggestions...")
            styling = await self.get_styling_suggestions(items, customer_id)
            flow_result["steps"]["styling_suggestions"] = styling
            
            flow_result["status"] = "completed"
            logger.info(f"✅ Purchase flow completed for order {flow_result['order_id']}")
            
        except Exception as e:
            logger.error(f"Error in purchase flow: {e}")
            flow_result["status"] = "error"
            flow_result["error"] = str(e)
        
        return flow_result
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global orchestrator instance
orchestrator = SalesOrchestrator()


async def main():
    """Test the orchestrator"""
    logger.info("Testing Sales Orchestrator...")
    
    # Test recommendations
    intent = {
        "is_shopping": True,
        "occasion": "weekend_trip",
        "style_preference": "casual",
        "budget": "mid"
    }
    
    recommendations = await orchestrator.get_recommendations(
        user_id="CUST001",
        intent=intent,
        context={}
    )
    
    logger.info(f"Got {len(recommendations)} recommendations")
    
    await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
