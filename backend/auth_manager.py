"""
Authentication Manager for multi-channel retail system.

This module handles:
- Password hashing and verification (bcrypt)
- Customer signup with dual-write (CSV + Supabase)
- Login validation (phone + password)
- QR token generation and verification for kiosk auth
- Session token management

Designed to work alongside session_manager.py without breaking existing functionality.
"""

import csv
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import bcrypt
import pandas as pd

logger = logging.getLogger(__name__)

# File paths
DATA_DIR = Path(__file__).parent / "data"
CUSTOMERS_CSV = DATA_DIR / "customers.csv"

# In-memory stores (same pattern as session_manager.py)
# Stores password hashes: phone_number -> bcrypt_hash
PASSWORD_STORE: Dict[str, str] = {}

# QR token store: qr_token -> {phone, expires_at, customer_id}
QR_TOKEN_STORE: Dict[str, Dict[str, Any]] = {}

# QR token expiry (15 minutes for kiosk security)
QR_TOKEN_EXPIRY = timedelta(minutes=15)


# ===========================
# Password Management
# ===========================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hash string (encoded as utf-8)
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash.
    
    Args:
        password: Plain text password to verify
        hashed: Stored bcrypt hash
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def store_password(phone: str, password: str) -> None:
    """Store a password hash for a phone number in memory.
    
    Args:
        phone: Phone number (primary identifier)
        password: Plain text password to hash and store
    """
    if not phone or not password:
        raise ValueError("Phone and password are required")
    
    hashed = hash_password(password)
    PASSWORD_STORE[phone] = hashed
    logger.info(f"Password stored for phone: {phone}")


def check_password(phone: str, password: str) -> bool:
    """Check if a password matches the stored hash for a phone number.
    
    Args:
        phone: Phone number
        password: Plain text password to verify
        
    Returns:
        True if password matches stored hash, False otherwise
    """
    if not phone or not password:
        return False
    
    stored_hash = PASSWORD_STORE.get(phone)
    if not stored_hash:
        logger.warning(f"No password found for phone: {phone}")
        return False
    
    return verify_password(password, stored_hash)


# ===========================
# Customer Management
# ===========================

def generate_customer_id() -> str:
    """Generate a unique customer ID.
    
    Returns:
        Customer ID string (e.g., '10001', '10002')
    """
    try:
        df = pd.read_csv(CUSTOMERS_CSV)
        if len(df) == 0:
            return "10001"
        
        # Extract numeric IDs and find max
        numeric_ids = []
        for cid in df['customer_id'].astype(str):
            try:
                numeric_ids.append(int(cid))
            except ValueError:
                continue
        
        if numeric_ids:
            max_id = max(numeric_ids)
            return str(max_id + 1)
        else:
            return "10001"
    except Exception as e:
        logger.error(f"Error generating customer ID: {e}")
        # Fallback to UUID-based ID
        return str(10000 + int(hashlib.md5(uuid.uuid4().hex.encode()).hexdigest()[:6], 16) % 90000)


def phone_exists(phone: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if a phone number already exists in customers.csv.
    
    Args:
        phone: Phone number to check
        
    Returns:
        Tuple of (exists: bool, customer_record: dict or None)
    """
    try:
        df = pd.read_csv(CUSTOMERS_CSV)
        matches = df[df['phone_number'].astype(str) == str(phone)]
        
        if len(matches) > 0:
            record = matches.iloc[0].to_dict()
            # Clean NaN values
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
            return True, record
        
        return False, None
    except Exception as e:
        logger.error(f"Error checking phone existence: {e}")
        return False, None


def create_customer(
    name: str,
    phone: str,
    password: str,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    city: Optional[str] = None,
    building_name: Optional[str] = None,
    address_landmark: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new customer with password.
    
    This function:
    1. Checks if phone already exists
    2. Generates new customer_id
    3. Stores password hash in memory
    4. Writes customer to CSV
    5. Returns customer record
    
    Args:
        name: Customer name (required)
        phone: Phone number (required, must be unique)
        password: Plain text password (required)
        age: Customer age (optional)
        gender: Gender (optional)
        city: City (optional)
        building_name: Building name for address (optional)
        address_landmark: Address landmark (optional)
        
    Returns:
        Customer record dictionary
        
    Raises:
        ValueError: If phone already exists or required fields missing
    """
    # Validate required fields
    if not name or not phone or not password:
        raise ValueError("Name, phone, and password are required")
    
    # Check if phone already exists
    exists, existing = phone_exists(phone)
    if exists:
        raise ValueError(f"Phone number {phone} already registered")
    
    # Generate customer ID
    customer_id = generate_customer_id()
    
    # Store password hash (in-memory)
    store_password(phone, password)
    
    # Prepare customer record
    customer_record = {
        'customer_id': customer_id,
        'name': name,
        'age': age if age else '',
        'gender': gender if gender else '',
        'phone_number': phone,
        'city': city if city else '',
        'building_name': building_name if building_name else '',
        'address_landmark': address_landmark if address_landmark else '',
        'loyalty_tier': 'Bronze',  # Default tier
        'loyalty_points': 0,
        'device_preference': 'web',
        'total_spend': 0.0,
        'items_purchased': 0,
        'average_rating': 0.0,
        'days_since_last_purchase': 0,
        'satisfaction': 'Neutral',
        'purchase_history': '[]',
    }
    
    # Write to CSV
    try:
        # Check if file exists and has header
        file_exists = CUSTOMERS_CSV.exists()
        
        with open(CUSTOMERS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=customer_record.keys())
            
            # Write header if file is new
            if not file_exists or CUSTOMERS_CSV.stat().st_size == 0:
                writer.writeheader()
            
            writer.writerow(customer_record)
        
        logger.info(f"Customer created: {customer_id} for phone {phone}")
        return customer_record
        
    except Exception as e:
        logger.error(f"Failed to write customer to CSV: {e}")
        raise


def validate_login(phone: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate login credentials (phone + password).
    
    Args:
        phone: Phone number
        password: Plain text password
        
    Returns:
        Tuple of (success: bool, customer_record: dict or None)
    """
    # Check if customer exists
    exists, customer = phone_exists(phone)
    if not exists:
        logger.warning(f"Login failed: Phone {phone} not found")
        return False, None
    
    # Verify password
    if not check_password(phone, password):
        logger.warning(f"Login failed: Invalid password for phone {phone}")
        return False, None
    
    logger.info(f"Login successful for phone {phone}")
    return True, customer


# ===========================
# QR Token Management
# ===========================

def generate_qr_token(phone: str, customer_id: str) -> str:
    """Generate a QR token for kiosk authentication.
    
    The token is a secure random string that maps to the user's phone and customer_id.
    Tokens expire after QR_TOKEN_EXPIRY (15 minutes).
    
    Args:
        phone: Customer phone number
        customer_id: Customer ID
        
    Returns:
        QR token string (32 character hex)
    """
    # Generate secure random token
    qr_token = secrets.token_hex(32)
    
    # Calculate expiry time
    expires_at = datetime.utcnow() + QR_TOKEN_EXPIRY
    
    # Store token mapping
    QR_TOKEN_STORE[qr_token] = {
        'phone': phone,
        'customer_id': customer_id,
        'expires_at': expires_at,
        'created_at': datetime.utcnow(),
    }
    
    logger.info(f"QR token generated for customer {customer_id}, expires at {expires_at}")
    return qr_token


def verify_qr_token(qr_token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Verify a QR token and return customer info if valid.
    
    Args:
        qr_token: QR token string to verify
        
    Returns:
        Tuple of (valid: bool, customer_info: dict or None)
        customer_info contains: phone, customer_id
    """
    # Check if token exists
    if qr_token not in QR_TOKEN_STORE:
        logger.warning(f"QR token not found: {qr_token}")
        return False, None
    
    token_data = QR_TOKEN_STORE[qr_token]
    
    # Check if token expired
    if datetime.utcnow() > token_data['expires_at']:
        logger.warning(f"QR token expired: {qr_token}")
        # Clean up expired token
        del QR_TOKEN_STORE[qr_token]
        return False, None
    
    # Token is valid - return customer info
    customer_info = {
        'phone': token_data['phone'],
        'customer_id': token_data['customer_id'],
    }
    
    logger.info(f"QR token verified for customer {customer_info['customer_id']}")
    
    # Token is single-use - remove after verification
    del QR_TOKEN_STORE[qr_token]
    
    return True, customer_info


def cleanup_expired_qr_tokens() -> int:
    """Remove expired QR tokens from memory.
    
    Returns:
        Number of tokens cleaned up
    """
    now = datetime.utcnow()
    expired_tokens = [
        token for token, data in QR_TOKEN_STORE.items()
        if now > data['expires_at']
    ]
    
    for token in expired_tokens:
        del QR_TOKEN_STORE[token]
    
    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired QR tokens")
    
    return len(expired_tokens)


# ===========================
# Initialization
# ===========================

def load_existing_passwords() -> None:
    """Load existing customer phone numbers and create default passwords.
    
    For existing customers (from customers.csv), we create a default password
    to ensure they can login via the website immediately.
    
    Default password: "Reebok@123" (should be changed after first login)
    
    This is a migration strategy - customers can:
    1. Login with default password, OR
    2. Continue using WhatsApp (phone-only) flow
    """
    DEFAULT_PASSWORD = "Reebok@123"
    
    try:
        df = pd.read_csv(CUSTOMERS_CSV)
        logger.info(f"Loading {len(df)} existing customers from CSV...")
        
        # Create default passwords for all existing customers
        password_count = 0
        for _, row in df.iterrows():
            phone = str(row['phone_number']).strip()
            if phone and phone not in PASSWORD_STORE:
                try:
                    # Store default password hash
                    hashed = hash_password(DEFAULT_PASSWORD)
                    PASSWORD_STORE[phone] = hashed
                    password_count += 1
                except Exception as e:
                    logger.warning(f"Failed to create default password for phone {phone}: {e}")
        
        logger.info(f"✅ Created default passwords for {password_count} existing customers")
        logger.info(f"📌 Default password: '{DEFAULT_PASSWORD}' (users should change this)")
        
    except Exception as e:
        logger.error(f"Error loading customers: {e}")


# Load existing customers on module import
load_existing_passwords()

logger.info("🔐 Auth manager initialized successfully")
