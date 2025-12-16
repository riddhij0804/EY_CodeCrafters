"""
Idempotency Manager - Prevents Duplicate Transactions
Member 4 Responsibility: Ensure same order cannot be paid twice
"""
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class IdempotencyRecord:
    """
    Record of an idempotent operation
    """
    key: str
    order_id: str
    operation_type: str  # 'checkout', 'payment', 'refund', etc.
    created_at: str
    expires_at: str
    request_hash: str
    response: Optional[Dict] = None
    status: str = "PENDING"  # PENDING, COMPLETED, FAILED
    
    def to_dict(self) -> Dict:
        return asdict(self)


class IdempotencyManager:
    """
    Manages idempotency keys to prevent duplicate operations
    
    Key Features:
    - Same cart cannot be checked out twice
    - Same payment cannot be processed twice
    - Same refund cannot be triggered twice
    """
    
    def __init__(self):
        # In production, this would be Redis or a database table
        # For now, using in-memory dictionary
        self._store: Dict[str, IdempotencyRecord] = {}
        self.expiry_hours = 24  # Idempotency keys expire after 24 hours
    
    def generate_key(
        self,
        user_id: str,
        operation_type: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Generate idempotency key based on user and cart/payment data
        
        Args:
            user_id: User identifier
            operation_type: Type of operation (checkout, payment, refund)
            data: Operation data to hash
            
        Returns:
            Idempotency key
        """
        # Create deterministic hash of cart/payment data
        data_string = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_string.encode()).hexdigest()
        
        # Format: {user_id}_{operation}_{data_hash}_{timestamp_bucket}
        # Timestamp bucket ensures same operation can happen again after time window
        timestamp_bucket = datetime.utcnow().strftime("%Y%m%d%H")
        
        key = f"{user_id}_{operation_type}_{data_hash[:16]}_{timestamp_bucket}"
        
        logger.info(f"Generated idempotency key: {key}")
        return key
    
    def check_duplicate(
        self,
        key: str,
        request_data: Dict[str, Any]
    ) -> Optional[IdempotencyRecord]:
        """
        Check if operation has already been performed
        
        Args:
            key: Idempotency key to check
            request_data: Current request data
            
        Returns:
            Existing record if duplicate found, None otherwise
        """
        if key not in self._store:
            logger.info(f"No duplicate found for key: {key}")
            return None
        
        record = self._store[key]
        
        # Check if record has expired
        expires_at = datetime.fromisoformat(record.expires_at)
        if datetime.utcnow() > expires_at:
            logger.info(f"Idempotency record expired for key: {key}")
            del self._store[key]
            return None
        
        # Verify request hash matches
        request_hash = hashlib.sha256(
            json.dumps(request_data, sort_keys=True).encode()
        ).hexdigest()
        
        if record.request_hash != request_hash:
            logger.warning(
                f"Request hash mismatch for key {key}. "
                f"Possible collision or different request with same key."
            )
            return None
        
        logger.warning(
            f"DUPLICATE OPERATION DETECTED! Key: {key}, "
            f"Original order: {record.order_id}, Status: {record.status}"
        )
        
        return record
    
    def register_operation(
        self,
        key: str,
        order_id: str,
        operation_type: str,
        request_data: Dict[str, Any]
    ) -> IdempotencyRecord:
        """
        Register a new operation with idempotency key
        
        Args:
            key: Idempotency key
            order_id: Associated order ID
            operation_type: Type of operation
            request_data: Request data to hash
            
        Returns:
            Created idempotency record
        """
        request_hash = hashlib.sha256(
            json.dumps(request_data, sort_keys=True).encode()
        ).hexdigest()
        
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=self.expiry_hours)
        
        record = IdempotencyRecord(
            key=key,
            order_id=order_id,
            operation_type=operation_type,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            request_hash=request_hash,
            status="PENDING"
        )
        
        self._store[key] = record
        
        logger.info(
            f"Registered idempotency record: {key} for order {order_id}"
        )
        
        return record
    
    def mark_completed(
        self,
        key: str,
        response: Dict[str, Any]
    ) -> bool:
        """
        Mark operation as completed
        
        Args:
            key: Idempotency key
            response: Operation response to cache
            
        Returns:
            True if marked successfully, False if key not found
        """
        if key not in self._store:
            logger.error(f"Cannot mark completed: key {key} not found")
            return False
        
        self._store[key].status = "COMPLETED"
        self._store[key].response = response
        
        logger.info(f"Marked operation as completed: {key}")
        return True
    
    def mark_failed(
        self,
        key: str,
        error: str
    ) -> bool:
        """
        Mark operation as failed
        
        Args:
            key: Idempotency key
            error: Error message
            
        Returns:
            True if marked successfully, False if key not found
        """
        if key not in self._store:
            logger.error(f"Cannot mark failed: key {key} not found")
            return False
        
        self._store[key].status = "FAILED"
        self._store[key].response = {"error": error}
        
        logger.info(f"Marked operation as failed: {key}")
        return True
    
    def cleanup_expired(self) -> int:
        """
        Remove expired idempotency records
        
        Returns:
            Number of records cleaned up
        """
        now = datetime.utcnow()
        expired_keys = []
        
        for key, record in self._store.items():
            expires_at = datetime.fromisoformat(record.expires_at)
            if now > expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._store[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired idempotency records")
        
        return len(expired_keys)
    
    def get_record(self, key: str) -> Optional[IdempotencyRecord]:
        """
        Retrieve idempotency record by key
        
        Args:
            key: Idempotency key
            
        Returns:
            Idempotency record if found, None otherwise
        """
        return self._store.get(key)


class PaymentIdempotencyValidator:
    """
    Specialized validator for payment operations
    Ensures payment cannot succeed twice for same order
    """
    
    def __init__(self, idempotency_manager: IdempotencyManager):
        self.idempotency_manager = idempotency_manager
    
    def validate_payment_request(
        self,
        user_id: str,
        order_id: str,
        amount: float,
        payment_method: str,
        additional_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Validate payment request and check for duplicates
        
        Args:
            user_id: User identifier
            order_id: Order identifier
            amount: Payment amount
            payment_method: Payment method used
            additional_data: Additional payment data
            
        Returns:
            Validation result with status and message
        """
        # Create payment data for idempotency check
        payment_data = {
            "order_id": order_id,
            "amount": amount,
            "payment_method": payment_method,
            **(additional_data or {})
        }
        
        # Generate idempotency key
        key = self.idempotency_manager.generate_key(
            user_id=user_id,
            operation_type="payment",
            data=payment_data
        )
        
        # Check for duplicate
        existing_record = self.idempotency_manager.check_duplicate(
            key=key,
            request_data=payment_data
        )
        
        if existing_record:
            if existing_record.status == "COMPLETED":
                return {
                    "status": "DUPLICATE",
                    "allowed": False,
                    "message": "Payment already processed for this order",
                    "original_order_id": existing_record.order_id,
                    "idempotency_key": key,
                    "action": "RETURN_ORIGINAL_RESPONSE"
                }
            elif existing_record.status == "PENDING":
                return {
                    "status": "IN_PROGRESS",
                    "allowed": False,
                    "message": "Payment is already being processed",
                    "original_order_id": existing_record.order_id,
                    "idempotency_key": key,
                    "action": "WAIT_OR_RETRY_LATER"
                }
            else:  # FAILED
                # Allow retry if previous attempt failed
                logger.info(
                    f"Previous payment attempt failed for key {key}. "
                    f"Allowing retry."
                )
        
        # Register new payment operation
        self.idempotency_manager.register_operation(
            key=key,
            order_id=order_id,
            operation_type="payment",
            request_data=payment_data
        )
        
        return {
            "status": "VALID",
            "allowed": True,
            "message": "Payment request is valid",
            "idempotency_key": key,
            "action": "PROCEED"
        }
    
    def handle_duplicate_payment(
        self,
        order_id: str,
        duplicate_payment_id: str,
        amount: float
    ) -> Dict[str, Any]:
        """
        Handle case where duplicate payment was detected after processing
        
        Args:
            order_id: Original order ID
            duplicate_payment_id: ID of duplicate payment transaction
            amount: Amount to refund
            
        Returns:
            Remediation plan
        """
        logger.critical(
            f"DUPLICATE PAYMENT DETECTED AFTER PROCESSING! "
            f"Order: {order_id}, Duplicate Payment: {duplicate_payment_id}"
        )
        
        return {
            "severity": "CRITICAL",
            "action": "AUTO_REFUND",
            "order_id": order_id,
            "duplicate_payment_id": duplicate_payment_id,
            "refund_amount": amount,
            "steps": [
                "Lock order for investigation",
                "Initiate automatic refund for duplicate payment",
                "Notify customer of the error",
                "Alert fraud detection system",
                "Create incident report"
            ],
            "customer_message": (
                "We detected a duplicate payment for your order. "
                "A full refund has been initiated and will be processed within 5-7 business days. "
                "We apologize for the inconvenience."
            )
        }


# Global idempotency manager instance
idempotency_manager = IdempotencyManager()
payment_validator = PaymentIdempotencyValidator(idempotency_manager)
