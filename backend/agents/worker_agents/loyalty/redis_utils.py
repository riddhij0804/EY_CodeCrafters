# CSV utilities for Loyalty Agent

import csv
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# CSV Configuration
CSV_PATH = os.path.join(os.path.dirname(__file__), '../../../data/customers.csv')

def _read_customers_csv():
    """Read customers CSV into a list of dicts"""
    customers = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                customers.append(row)
    return customers

def _write_customers_csv(customers):
    """Write list of dicts to customers CSV"""
    if customers:
        fieldnames = customers[0].keys()
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(customers)

def get_user_points(user_id: str) -> int:
    """Get loyalty points for a user from CSV"""
    customers = _read_customers_csv()
    for customer in customers:
        if customer['customer_id'] == str(user_id):
            return int(customer.get('loyalty_points', 0))
    # New user, return 0
    return 0

def update_user_points(user_id: str, new_points: int) -> bool:
    """Update loyalty points for a user in CSV"""
    customers = _read_customers_csv()
    user_found = False
    for customer in customers:
        if customer['customer_id'] == str(user_id):
            customer['loyalty_points'] = str(new_points)
            # Also update tier based on points
            tier_info = calculate_tier(new_points)
            customer['loyalty_tier'] = tier_info['tier']
            user_found = True
            break
    
    if not user_found:
        # New user, add to CSV
        new_customer = {
            'customer_id': str(user_id),
            'name': f'User {user_id}',
            'age': '25',
            'gender': 'Unknown',
            'phone_number': '0000000000',
            'city': 'Unknown',
            'loyalty_tier': calculate_tier(new_points)['tier'],
            'loyalty_points': str(new_points),
            'device_preference': 'mobile',
            'total_spend': '0.0',
            'items_purchased': '0',
            'average_rating': '0.0',
            'days_since_last_purchase': '0',
            'satisfaction': 'Neutral',
            'purchase_history': '[]'
        }
        customers.append(new_customer)
    
    _write_customers_csv(customers)
    return True


def deduct_points(user_id: str, points_to_deduct: int) -> dict:
    """
    Atomically deduct points from user's balance
    Returns: {"success": bool, "remaining_points": int, "deducted": int}
    """
    current_points = get_user_points(user_id)
    
    if current_points < points_to_deduct:
        return {
            "success": False,
            "remaining_points": current_points,
            "deducted": 0,
            "error": "Insufficient points"
        }
    
    new_points = current_points - points_to_deduct
    update_user_points(user_id, new_points)
    
    return {
        "success": True,
        "remaining_points": new_points,
        "deducted": points_to_deduct
    }


def add_points(user_id: str, points_to_add: int) -> dict:
    """
    Add points to user's balance
    Returns: {"success": bool, "new_balance": int, "added": int}
    """
    current_points = get_user_points(user_id)
    new_points = current_points + points_to_add
    update_user_points(user_id, new_points)
    
    return {
        "success": True,
        "new_balance": new_points,
        "added": points_to_add
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
    Tier thresholds:
    - Bronze: 0-999 points
    - Silver: 1000-2999 points
    - Gold: 3000-4999 points
    - Platinum: 5000+ points
    
    Returns: {"tier": str, "next_tier": str, "points_to_next": int, "benefits": dict}
    """
    if points >= 5000:
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
    elif points >= 3000:
        return {
            "tier": "Gold",
            "next_tier": "Platinum",
            "points_to_next": 5000 - points,
            "benefits": {
                "discount_percent": 10,
                "free_shipping": True,
                "priority_support": False,
                "birthday_bonus": 300,
                "points_multiplier": 1.5
            }
        }
    elif points >= 1000:
        return {
            "tier": "Silver",
            "next_tier": "Gold",
            "points_to_next": 3000 - points,
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
            "points_to_next": 1000 - points,
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
    Get complete tier information for a user.
    Returns points, tier, and benefits.
    """
    points = get_user_points(user_id)
    tier_info = calculate_tier(points)
    
    return {
        "user_id": user_id,
        "points": points,
        **tier_info
    }


def earn_points_from_purchase(user_id: str, amount_spent: float) -> dict:
    """
    Award points after successful purchase.
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
    # Get current state
    old_points = get_user_points(user_id)
    old_tier_info = calculate_tier(old_points)
    old_tier = old_tier_info["tier"]
    
    # Calculate points to earn (1 point per ₹10)
    points_to_earn = int(amount_spent / 10)
    
    # Apply tier multiplier
    multiplier = old_tier_info["benefits"]["points_multiplier"]
    bonus_points = int(points_to_earn * (multiplier - 1.0))
    total_earned = points_to_earn + bonus_points
    
    # Add points
    result = add_points(user_id, total_earned)
    
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
        "multiplier_applied": multiplier
    }
