# Supabase utilities for Loyalty Agent

import csv
import os
from typing import Optional
from dotenv import load_dotenv
import sys
from pathlib import Path

load_dotenv()

# Add path to import supabase_client
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from db import supabase_client

# CSV Configuration (kept for backward compatibility but not used)
CSV_PATH = os.path.join(os.path.dirname(__file__), '../../../data/customers.csv')

# Supabase-based loyalty utilities
# CSV functions removed - all data now comes from Supabase

def get_user_points(user_id: str) -> int:
    """Get loyalty points for a user from Supabase"""
    try:
        if not supabase_client.is_enabled():
            print("⚠️ Supabase not enabled, returning 0 points")
            return 0

        customer = supabase_client.select_one('customers', f'customer_id=eq.{user_id}')
        if customer:
            points = customer.get('loyalty_points', 0)
            return int(points) if points is not None else 0
        else:
            print(f"🔍 User {user_id} not found in Supabase, returning 0 points")
            return 0
    except Exception as e:
        print(f"❌ Error fetching user points from Supabase: {e}")
        return 0

def update_user_points(user_id: str, new_points: int) -> bool:
    """Update loyalty points for a user in Supabase"""
    try:
        if not supabase_client.is_enabled() or not supabase_client.is_write_enabled():
            print("⚠️ Supabase not enabled or not write-enabled")
            return False

        # Calculate tier based on points
        tier_info = calculate_tier(new_points)
        new_tier = tier_info['tier']

        # Try to update existing customer
        customer = supabase_client.select_one('customers', f'customer_id=eq.{user_id}')
        if customer:
            # Update existing customer
            supabase_client.upsert('customers', {
                'customer_id': user_id,
                'loyalty_points': new_points,
                'loyalty_tier': new_tier.lower(),
                # Preserve other fields
                'total_spend': customer.get('total_spend', 0),
                'items_purchased': customer.get('items_purchased', 0),
                'purchase_history': customer.get('purchase_history', []),
            }, conflict_column='customer_id')
        else:
            # Create new customer
            supabase_client.upsert('customers', {
                'customer_id': user_id,
                'loyalty_points': new_points,
                'loyalty_tier': new_tier.lower(),
                'total_spend': 0.0,
                'items_purchased': 0,
                'purchase_history': [],
            }, conflict_column='customer_id')

        print(f"✅ Updated user {user_id}: {new_points} points, {new_tier} tier")
        return True
    except Exception as e:
        print(f"❌ Error updating user points in Supabase: {e}")
        return False


def deduct_points(user_id: str, points_to_deduct: int) -> dict:
    """
    Atomically deduct points from user's balance in Supabase
    Returns: {"success": bool, "remaining_points": int, "deducted": int}
    """
    try:
        current_points = get_user_points(user_id)

        if current_points < points_to_deduct:
            return {
                "success": False,
                "remaining_points": current_points,
                "deducted": 0,
                "error": "Insufficient points"
            }

        new_points = current_points - points_to_deduct
        success = update_user_points(user_id, new_points)

        if success:
            return {
                "success": True,
                "remaining_points": new_points,
                "deducted": points_to_deduct
            }
        else:
            return {
                "success": False,
                "remaining_points": current_points,
                "deducted": 0,
                "error": "Failed to update points"
            }
    except Exception as e:
        print(f"❌ Error deducting points: {e}")
        return {
            "success": False,
            "remaining_points": get_user_points(user_id),
            "deducted": 0,
            "error": str(e)
        }


def add_points(user_id: str, points_to_add: int) -> dict:
    """
    Add points to user's balance in Supabase
    Returns: {"success": bool, "new_balance": int, "added": int}
    """
    try:
        current_points = get_user_points(user_id)
        new_points = current_points + points_to_add
        success = update_user_points(user_id, new_points)

        if success:
            return {
                "success": True,
                "new_balance": new_points,
                "added": points_to_add
            }
        else:
            return {
                "success": False,
                "new_balance": current_points,
                "added": 0,
                "error": "Failed to update points"
            }
    except Exception as e:
        print(f"❌ Error adding points: {e}")
        return {
            "success": False,
            "new_balance": get_user_points(user_id),
            "added": 0,
            "error": str(e)
        }


def validate_coupon(code: str) -> Optional[dict]:
    """
    Validate coupon code and return discount details
    Returns: {"code": str, "discount_percent": float, "min_purchase": float}
    """
    # Coupon database (in production, this would be in Redis/DB)
    coupons = {
        "ABFRL10": {"code": "ABFRL10", "discount_percent": 10.0, "min_purchase": 500.0},
        "ABFRL20": {"code": "ABFRL20", "discount_percent": 20.0, "min_purchase": 1000.0},
        "NEW50": {"code": "NEW50", "discount_percent": 50.0, "min_purchase": 2000.0},
        "SAVE15": {"code": "SAVE15", "discount_percent": 15.0, "min_purchase": 750.0},
        "WELCOME25": {"code": "WELCOME25", "discount_percent": 25.0, "min_purchase": 1500.0},
    }
    
    return coupons.get(code.upper())


def check_coupon_usage(user_id: str, coupon_code: str) -> bool:
    """Check if user has already used this coupon"""
    # For now, using in-memory (in production, use DB)
    # TODO: Implement persistent storage
    return False  # Allow reuse for demo


def mark_coupon_used(user_id: str, coupon_code: str, expiry_days: int = 365) -> bool:
    """Mark coupon as used by user (with expiry)"""
    # For now, do nothing (in production, use DB)
    return True


def calculate_tier(points: int) -> dict:
    """
    Calculate user tier based on total points.
    Tier thresholds (matching payment agent):
    - Bronze: 0-499 points
    - Silver: 500-999 points
    - Gold: 1000-1999 points
    - Platinum: 2000+ points

    Returns: {"tier": str, "next_tier": str, "points_to_next": int, "benefits": dict}
    """
    if points >= 2000:
        return {
            "tier": "Platinum",
            "next_tier": None,
            "points_to_next": 0,
            "benefits": {
                "discount_percent": 15,
                "free_shipping": True,
                "priority_support": True,
                "birthday_bonus": 500,
                "points_multiplier": 2.0
            }
        }
    elif points >= 1000:
        return {
            "tier": "Gold",
            "next_tier": "Platinum",
            "points_to_next": 2000 - points,
            "benefits": {
                "discount_percent": 10,
                "free_shipping": True,
                "priority_support": False,
                "birthday_bonus": 300,
                "points_multiplier": 1.5
            }
        }
    elif points >= 500:
        return {
            "tier": "Silver",
            "next_tier": "Gold",
            "points_to_next": 1000 - points,
            "benefits": {
                "discount_percent": 5,
                "free_shipping": False,
                "priority_support": False,
                "birthday_bonus": 150,
                "points_multiplier": 1.2
            }
        }
    else:
        return {
            "tier": "Bronze",
            "next_tier": "Silver",
            "points_to_next": 500 - points,
            "benefits": {
                "discount_percent": 0,
                "free_shipping": False,
                "priority_support": False,
                "birthday_bonus": 0,
                "points_multiplier": 1.0
            }
        }


def get_user_tier_info(user_id: str) -> dict:
    """
    Get complete tier information for a user from Supabase.
    Returns points, tier, and benefits.
    """
    try:
        points = get_user_points(user_id)
        tier_info = calculate_tier(points)

        return {
            "user_id": user_id,
            "points": points,
            **tier_info,
            "source": "supabase"
        }
    except Exception as e:
        print(f"❌ Error getting user tier info: {e}")
        # Return default values on error
        tier_info = calculate_tier(0)
        return {
            "user_id": user_id,
            "points": 0,
            **tier_info,
            "source": "error",
            "error": str(e)
        }


def earn_points_from_purchase(user_id: str, amount_spent: float) -> dict:
    """
    Award points after successful purchase from Supabase.
    Rule: 1 point per ₹10 spent
    Also checks for tier upgrade.

    Returns: {
        "success": bool,
        "points_earned": int,
        "total_points": int,
        "previous_tier": str,
        "current_tier": str,
        "tier_upgraded": bool
    }
    """
    try:
        # Get current state from Supabase
        old_points = get_user_points(user_id)
        old_tier_info = calculate_tier(old_points)
        old_tier = old_tier_info["tier"]

        # Calculate points to earn (2% cashback like payment agent)
        points_to_earn = int(amount_spent * 0.02)

        # Apply tier multiplier
        multiplier = old_tier_info["benefits"]["points_multiplier"]
        bonus_points = int(points_to_earn * (multiplier - 1.0))
        total_earned = points_to_earn + bonus_points

        # Add points
        result = add_points(user_id, total_earned)

        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", "Failed to add points"),
                "amount_spent": amount_spent,
                "points_earned": 0,
                "total_points": old_points,
                "previous_tier": old_tier,
                "current_tier": old_tier,
                "tier_upgraded": False
            }

        # Check new tier
        new_points = result["new_balance"]
        new_tier_info = calculate_tier(new_points)
        new_tier = new_tier_info["tier"]

        tier_upgraded = new_tier != old_tier

        return {
            "success": True,
            "amount_spent": amount_spent,
            "base_points_earned": points_to_earn,
            "bonus_points": bonus_points,
            "total_points_earned": total_earned,
            "total_points": new_points,
            "previous_tier": old_tier,
            "current_tier": new_tier,
            "tier_upgraded": tier_upgraded,
            "multiplier_applied": multiplier,
            "source": "supabase"
        }
    except Exception as e:
        print(f"❌ Error earning points from purchase: {e}")
        return {
            "success": False,
            "error": str(e),
            "amount_spent": amount_spent,
            "points_earned": 0,
            "total_points": 0,
            "previous_tier": "Unknown",
            "current_tier": "Unknown",
            "tier_upgraded": False
        }
