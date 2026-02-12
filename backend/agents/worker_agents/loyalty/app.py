# Loyalty Agent - FastAPI Server
# Endpoints: GET /loyalty/points/{user_id}, POST /loyalty/apply, POST /loyalty/add-points, GET /loyalty/validate-coupon/{code}

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
from datetime import datetime
import redis_utils
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from db import supabase_client

app = FastAPI(
    title="Loyalty Agent",
    description="Loyalty points and coupon management system",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class ApplyLoyaltyRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    cart_total: float = Field(..., gt=0, description="Cart total amount")
    applied_coupon: Optional[str] = Field(None, description="Coupon code to apply")
    loyalty_points_used: int = Field(default=0, ge=0, description="Loyalty points to redeem")


class AddPointsRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    points: int = Field(..., gt=0, description="Points to add")
    reason: str = Field(default="purchase", description="Reason for adding points")


class LoyaltyResponse(BaseModel):
    success: bool
    original_total: float
    discount_from_coupon: float
    discount_from_points: float
    final_total: float
    coupon_applied: Optional[str]
    points_used: int
    points_remaining: int
    message: str


class PointsResponse(BaseModel):
    user_id: str
    points: int


class CouponValidationResponse(BaseModel):
    valid: bool
    coupon_code: Optional[str]
    discount_percent: Optional[float]
    min_purchase: Optional[float]
    message: str


class PromotionRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    cart_total: float = Field(..., gt=0, description="Cart total amount")
    category: Optional[str] = Field(None, description="Product category")


class PromotionResponse(BaseModel):
    applicable_promotions: list
    best_promotion: Optional[dict]
    total_savings: float
    message: str


class RulesEngineRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    purchase_amount: float = Field(..., gt=0, description="Purchase amount")
    items_count: int = Field(..., ge=1, description="Number of items")


class RulesEngineResponse(BaseModel):
    points_earned: int
    tier_bonus: float
    special_bonus: Optional[str]
    total_points: int
    message: str


class CalculateDiscountsRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    cart_total: float = Field(..., gt=0, description="Cart total amount")


class CalculateDiscountsResponse(BaseModel):
    success: bool
    original_total: float
    tier_discount_percent: float
    tier_discount_amount: float
    best_coupon: Optional[dict]
    coupon_discount_amount: float
    best_promotion: Optional[dict]
    promotion_discount_amount: float
    total_discount_amount: float
    final_total: float
    message: str


# ==========================================
# ROUTES
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Loyalty Agent",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/loyalty/points/{user_id}", response_model=PointsResponse)
async def get_user_points(user_id: str):
    """Get loyalty points for a user"""
    try:
        points = redis_utils.get_user_points(user_id)
        return PointsResponse(user_id=user_id, points=points)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/loyalty/tier/{user_id}")
async def get_user_tier(user_id: str):
    """Get complete tier information for a user including points, tier, and benefits"""
    try:
        print(f"🔍 Fetching loyalty info for user: {user_id}")
        
        # Always use Supabase as the primary source of truth
        if supabase_client.is_enabled():
            try:
                customer = supabase_client.select_one('customers', f'customer_id=eq.{user_id}')
                print(f"📊 Supabase customer data: {customer}")
                
                if customer:
                    points = int(customer.get('loyalty_points', 0))
                    tier = customer.get('loyalty_tier', 'bronze').capitalize()
                    
                    print(f"✅ Retrieved from Supabase - Points: {points}, Tier: {tier}")
                    
                    # Calculate tier info for benefits
                    tier_data = redis_utils.calculate_tier(points)
                    
                    return {
                        "user_id": user_id,
                        "points": points,
                        "tier": tier,
                        "benefits": tier_data.get("benefits", {}),
                        "next_tier": tier_data.get("next_tier"),
                        "points_to_next_tier": tier_data.get("points_to_next_tier", 0),
                        "source": "supabase"
                    }
                else:
                    # Customer not found in Supabase, return default values
                    print(f"⚠️ Customer {user_id} not found in Supabase, returning defaults")
                    tier_data = redis_utils.calculate_tier(0)
                    return {
                        "user_id": user_id,
                        "points": 0,
                        "tier": "bronze",
                        "benefits": tier_data.get("benefits", {}),
                        "next_tier": tier_data.get("next_tier"),
                        "points_to_next_tier": tier_data.get("points_to_next_tier", 0),
                        "source": "default"
                    }
            except Exception as e:
                print(f"❌ Error fetching from Supabase: {e}")
                # Don't fallback to Redis, return error
                raise HTTPException(status_code=500, detail=f"Supabase error: {str(e)}")
        else:
            print("⚠️ Supabase is not enabled")
            raise HTTPException(status_code=503, detail="Supabase is not available")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/loyalty/add-points", response_model=dict)
async def add_points(request: AddPointsRequest):
    """Add loyalty points to a user's account"""
    try:
        result = redis_utils.add_points(request.user_id, request.points)
        return {
            "success": result["success"],
            "user_id": request.user_id,
            "points_added": result["added"],
            "new_balance": result["new_balance"],
            "reason": request.reason,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/loyalty/earn-from-purchase")
async def earn_points_from_purchase(user_id: str, amount_spent: float):
    """
    Award loyalty points after successful payment.
    Rule: 1 point per ₹10 spent (with tier multiplier bonus)
    Automatically upgrades tier if thresholds crossed.
    """
    try:
        if amount_spent <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        result = redis_utils.earn_points_from_purchase(user_id, amount_spent)
        
        # Build response message
        message = f"🎉 Earned {result['total_points_earned']} loyalty points!"
        
        if result['bonus_points'] > 0:
            message += f" (Base: {result['base_points_earned']}, Bonus: {result['bonus_points']})"
        
        if result['tier_upgraded']:
            message += f"\n\n🏆 Tier Upgraded: {result['previous_tier']} → {result['current_tier']}!"
        
        return {
            **result,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/loyalty/validate-coupon/{code}", response_model=CouponValidationResponse)
async def validate_coupon(code: str):
    """Validate a coupon code"""
    try:
        coupon = redis_utils.validate_coupon(code)
        
        if coupon:
            return CouponValidationResponse(
                valid=True,
                coupon_code=coupon["code"],
                discount_percent=coupon["discount_percent"],
                min_purchase=coupon["min_purchase"],
                message=f"Valid coupon: {coupon['discount_percent']}% off on purchases above ₹{coupon['min_purchase']}"
            )
        else:
            return CouponValidationResponse(
                valid=False,
                coupon_code=None,
                discount_percent=None,
                min_purchase=None,
                message="Invalid coupon code"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/loyalty/apply", response_model=LoyaltyResponse)
async def apply_loyalty(request: ApplyLoyaltyRequest):
    """
    Apply loyalty benefits (coupons + points) to a purchase
    Process:
    1. Validate and apply coupon (if provided)
    2. Apply loyalty points redemption
    3. Calculate final amount
    """
    try:
        original_total = request.cart_total
        current_total = original_total
        discount_from_coupon = 0.0
        discount_from_points = 0.0
        coupon_applied = None
        points_used = 0
        
        # Step 1: Apply Coupon
        if request.applied_coupon:
            coupon = redis_utils.validate_coupon(request.applied_coupon)
            
            if not coupon:
                raise HTTPException(status_code=400, detail="Invalid coupon code")
            
            # Check minimum purchase requirement
            if original_total < coupon["min_purchase"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Minimum purchase of ₹{coupon['min_purchase']} required for this coupon"
                )
            
            # Check if user already used this coupon
            if redis_utils.check_coupon_usage(request.user_id, request.applied_coupon):
                raise HTTPException(
                    status_code=400,
                    detail="You have already used this coupon"
                )
            
            # Apply coupon discount
            discount_from_coupon = (original_total * coupon["discount_percent"]) / 100
            current_total -= discount_from_coupon
            coupon_applied = request.applied_coupon
            
            # Mark coupon as used
            redis_utils.mark_coupon_used(request.user_id, request.applied_coupon)
        
        # Step 2: Apply Loyalty Points
        if request.loyalty_points_used > 0:
            user_points = redis_utils.get_user_points(request.user_id)
            
            if user_points < request.loyalty_points_used:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient points. You have {user_points} points."
                )
            
            # Deduct points (1 point = ₹1)
            result = redis_utils.deduct_points(request.user_id, request.loyalty_points_used)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result.get("error", "Failed to deduct points"))
            
            discount_from_points = request.loyalty_points_used
            current_total -= discount_from_points
            points_used = request.loyalty_points_used
        
        # Ensure final total is not negative
        final_total = max(current_total, 0)
        
        # Get remaining points
        points_remaining = redis_utils.get_user_points(request.user_id)
        
        return LoyaltyResponse(
            success=True,
            original_total=original_total,
            discount_from_coupon=discount_from_coupon,
            discount_from_points=discount_from_points,
            final_total=final_total,
            coupon_applied=coupon_applied,
            points_used=points_used,
            points_remaining=points_remaining,
            message=f"Loyalty benefits applied successfully. Total savings: ₹{discount_from_coupon + discount_from_points}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/loyalty/check-promotions", response_model=PromotionResponse)
async def check_active_promotions(request: PromotionRequest):
    """
    Loyalty and Promotions Service: Mock rules engine for timed promotions
    Checks for active time-based promotions and applies the best one
    """
    try:
        from datetime import datetime, time
        
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime("%A")
        
        applicable_promotions = []
        
        # Time-based promotions
        promotions = [
            {
                "name": "Early Bird Special",
                "discount": 15,
                "condition": "6 AM - 10 AM",
                "active": 6 <= current_hour < 10,
                "min_purchase": 500
            },
            {
                "name": "Lunch Hour Deal",
                "discount": 10,
                "condition": "12 PM - 2 PM",
                "active": 12 <= current_hour < 14,
                "min_purchase": 300
            },
            {
                "name": "Happy Hours",
                "discount": 20,
                "condition": "5 PM - 8 PM",
                "active": 17 <= current_hour < 20,
                "min_purchase": 1000
            },
            {
                "name": "Weekend Bonanza",
                "discount": 25,
                "condition": "Saturday & Sunday",
                "active": current_day in ["Saturday", "Sunday"],
                "min_purchase": 1500
            },
            {
                "name": "Midnight Flash Sale",
                "discount": 30,
                "condition": "12 AM - 2 AM",
                "active": 0 <= current_hour < 2,
                "min_purchase": 2000
            }
        ]
        
        # Filter applicable promotions
        for promo in promotions:
            if promo["active"] and request.cart_total >= promo["min_purchase"]:
                applicable_promotions.append({
                    "name": promo["name"],
                    "discount": promo["discount"],
                    "condition": promo["condition"],
                    "savings": (request.cart_total * promo["discount"]) / 100
                })
        
        # Find best promotion
        best_promotion = None
        max_savings = 0
        
        if applicable_promotions:
            best_promotion = max(applicable_promotions, key=lambda x: x["savings"])
            max_savings = best_promotion["savings"]
        
        return PromotionResponse(
            applicable_promotions=applicable_promotions,
            best_promotion=best_promotion,
            total_savings=max_savings,
            message=f"Found {len(applicable_promotions)} active promotion(s)" if applicable_promotions 
                    else "No active promotions at this time"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/loyalty/calculate-points", response_model=RulesEngineResponse)
async def calculate_loyalty_points(request: RulesEngineRequest):
    """
    Loyalty Rules Engine: Calculate points based on purchase
    Rules:
    - Base: 1 point per ₹100 spent
    - Tier bonus: Bronze (0%), Silver (10%), Gold (25%), Platinum (50%)
    - Special bonuses for bulk purchases
    """
    try:
        # Get user's current points to determine tier
        current_points = redis_utils.get_user_points(request.user_id)
        
        # Determine tier based on points
        if current_points < 500:
            tier = "Bronze"
            tier_multiplier = 1.0
        elif current_points < 2000:
            tier = "Silver"
            tier_multiplier = 1.1
        elif current_points < 5000:
            tier = "Gold"
            tier_multiplier = 1.25
        else:
            tier = "Platinum"
            tier_multiplier = 1.5
        
        # Base points calculation (1 point per ₹100)
        base_points = int(request.purchase_amount / 100)
        
        # Apply tier bonus
        points_with_tier = int(base_points * tier_multiplier)
        
        # Special bonuses
        special_bonus = None
        bonus_points = 0
        
        if request.items_count >= 10:
            bonus_points = 50
            special_bonus = "Bulk Purchase Bonus (+50 points)"
        elif request.purchase_amount >= 5000:
            bonus_points = 100
            special_bonus = "High Value Purchase (+100 points)"
        elif request.items_count >= 5:
            bonus_points = 20
            special_bonus = "Multi-item Bonus (+20 points)"
        
        # Total points to be awarded
        total_points = points_with_tier + bonus_points
        
        # Add points to user account
        redis_utils.add_points(request.user_id, total_points)
        
        return RulesEngineResponse(
            points_earned=base_points,
            tier_bonus=(tier_multiplier - 1.0) * 100,
            special_bonus=special_bonus,
            total_points=total_points,
            message=f"Earned {total_points} points! Current tier: {tier}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/loyalty/active-promotions")
async def get_active_promotions():
    """Get list of all available timed promotions"""
    from datetime import datetime
    
    current_hour = datetime.now().hour
    current_day = datetime.now().strftime("%A")
    
    promotions = [
        {
            "name": "Early Bird Special",
            "discount": "15%",
            "time": "6 AM - 10 AM",
            "min_purchase": "₹500",
            "active": 6 <= current_hour < 10
        },
        {
            "name": "Lunch Hour Deal",
            "discount": "10%",
            "time": "12 PM - 2 PM",
            "min_purchase": "₹300",
            "active": 12 <= current_hour < 14
        },
        {
            "name": "Happy Hours",
            "discount": "20%",
            "time": "5 PM - 8 PM",
            "min_purchase": "₹1000",
            "active": 17 <= current_hour < 20
        },
        {
            "name": "Weekend Bonanza",
            "discount": "25%",
            "time": "Saturday & Sunday",
            "min_purchase": "₹1500",
            "active": current_day in ["Saturday", "Sunday"]
        },
        {
            "name": "Midnight Flash Sale",
            "discount": "30%",
            "time": "12 AM - 2 AM",
            "min_purchase": "₹2000",
            "active": 0 <= current_hour < 2
        }
    ]
    
    active_count = sum(1 for p in promotions if p["active"])
    
    return {
        "promotions": promotions,
        "active_count": active_count,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/loyalty/calculate-discounts", response_model=CalculateDiscountsResponse)
async def calculate_discounts(request: CalculateDiscountsRequest):
    """
    Calculate all applicable discounts for a user's cart:
    - Tier-based discount
    - Best available coupon
    - Best active promotion
    Returns the final discounted total
    """
    try:
        original_total = request.cart_total
        
        # Get user tier and benefits
        tier_info = redis_utils.get_user_tier_info(request.user_id)
        tier_discount_percent = tier_info["benefits"]["discount_percent"]
        tier_discount_amount = (original_total * tier_discount_percent) / 100
        
        # Find best coupon
        best_coupon = None
        max_coupon_savings = 0
        coupons = [
            {"code": "ABFRL10", "discount_percent": 10.0, "min_purchase": 500.0},
            {"code": "ABFRL20", "discount_percent": 20.0, "min_purchase": 1000.0},
            {"code": "WELCOME25", "discount_percent": 25.0, "min_purchase": 1500.0},
        ]
        
        for coupon in coupons:
            if original_total >= coupon["min_purchase"]:
                savings = (original_total * coupon["discount_percent"]) / 100
                if savings > max_coupon_savings:
                    max_coupon_savings = savings
                    best_coupon = coupon
        
        coupon_discount_amount = max_coupon_savings
        
        # Find best promotion (reuse check-promotions logic)
        from datetime import datetime
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime("%A")
        
        promotions = [
            {"name": "Early Bird Special", "discount": 15, "min_purchase": 500, "active": 6 <= current_hour < 10},
            {"name": "Lunch Hour Deal", "discount": 10, "min_purchase": 300, "active": 12 <= current_hour < 14},
            {"name": "Happy Hours", "discount": 20, "min_purchase": 1000, "active": 17 <= current_hour < 20},
            {"name": "Weekend Bonanza", "discount": 25, "min_purchase": 1500, "active": current_day in ["Saturday", "Sunday"]},
            {"name": "Midnight Flash Sale", "discount": 30, "min_purchase": 2000, "active": 0 <= current_hour < 2},
        ]
        
        best_promotion = None
        max_promo_savings = 0
        
        for promo in promotions:
            if promo["active"] and original_total >= promo["min_purchase"]:
                savings = (original_total * promo["discount"]) / 100
                if savings > max_promo_savings:
                    max_promo_savings = savings
                    best_promotion = promo
        
        promotion_discount_amount = max_promo_savings
        
        # Calculate total discount (tier + coupon + promotion)
        # Note: We apply tier first, then the best of coupon/promotion
        total_discount_amount = tier_discount_amount + max(coupon_discount_amount, promotion_discount_amount)
        
        final_total = max(0, original_total - total_discount_amount)
        
        # Determine which one was applied
        applied_coupon = best_coupon if coupon_discount_amount >= promotion_discount_amount else None
        applied_promotion = best_promotion if promotion_discount_amount > coupon_discount_amount else None
        
        message = f"Applied {tier_discount_percent}% tier discount"
        if applied_coupon:
            message += f" + {applied_coupon['discount_percent']}% coupon ({applied_coupon['code']})"
        elif applied_promotion:
            message += f" + {applied_promotion['discount']}% promotion ({applied_promotion['name']})"
        
        return CalculateDiscountsResponse(
            success=True,
            original_total=original_total,
            tier_discount_percent=tier_discount_percent,
            tier_discount_amount=tier_discount_amount,
            best_coupon=applied_coupon,
            coupon_discount_amount=coupon_discount_amount if applied_coupon else 0,
            best_promotion=applied_promotion,
            promotion_discount_amount=promotion_discount_amount if applied_promotion else 0,
            total_discount_amount=total_discount_amount,
            final_total=final_total,
            message=message
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
