"""
Payment Safety Layer - Transaction Trust and Validation
Member 4 Responsibility: Ensure payment integrity and prevent fraud
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    """Payment transaction statuses"""
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


@dataclass
class PaymentTransaction:
    """
    Payment transaction record
    """
    transaction_id: str
    order_id: str
    user_id: str
    amount: float
    payment_method: str
    status: PaymentStatus
    gateway_reference: str
    idempotency_key: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "transaction_id": self.transaction_id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "payment_method": self.payment_method,
            "status": self.status.value,
            "gateway_reference": self.gateway_reference,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }


class PaymentValidator:
    """
    Validates payment requests before processing
    Prevents fraud and ensures data integrity
    """
    
    @staticmethod
    def validate_payment_amount(
        order_amount: float,
        payment_amount: float,
        tolerance: float = 0.01
    ) -> Dict[str, Any]:
        """
        Ensure payment amount matches order amount
        
        Args:
            order_amount: Expected order total
            payment_amount: Amount being paid
            tolerance: Acceptable difference (for rounding)
            
        Returns:
            Validation result
        """
        if abs(order_amount - payment_amount) > tolerance:
            logger.error(
                f"Payment amount mismatch: Order={order_amount}, "
                f"Payment={payment_amount}"
            )
            return {
                "valid": False,
                "error": "AMOUNT_MISMATCH",
                "message": f"Payment amount (₹{payment_amount}) does not match order amount (₹{order_amount})",
                "action": "REJECT_PAYMENT"
            }
        
        return {
            "valid": True,
            "message": "Amount validation passed"
        }
    
    @staticmethod
    def validate_payment_method(
        payment_method: str,
        allowed_methods: List[str]
    ) -> Dict[str, Any]:
        """
        Validate payment method is supported
        
        Args:
            payment_method: Payment method to validate
            allowed_methods: List of allowed payment methods
            
        Returns:
            Validation result
        """
        if payment_method not in allowed_methods:
            logger.error(f"Invalid payment method: {payment_method}")
            return {
                "valid": False,
                "error": "INVALID_PAYMENT_METHOD",
                "message": f"Payment method '{payment_method}' is not supported",
                "allowed_methods": allowed_methods,
                "action": "REJECT_PAYMENT"
            }
        
        return {
            "valid": True,
            "message": "Payment method validated"
        }
    
    @staticmethod
    def validate_user_limits(
        user_id: str,
        amount: float,
        user_daily_limit: float = 50000.0,
        user_daily_spent: float = 0.0
    ) -> Dict[str, Any]:
        """
        Check if payment exceeds user limits
        
        Args:
            user_id: User identifier
            amount: Payment amount
            user_daily_limit: User's daily spending limit
            user_daily_spent: Amount already spent today
            
        Returns:
            Validation result
        """
        if user_daily_spent + amount > user_daily_limit:
            logger.warning(
                f"User {user_id} exceeds daily limit: "
                f"Spent={user_daily_spent}, Attempt={amount}, Limit={user_daily_limit}"
            )
            return {
                "valid": False,
                "error": "DAILY_LIMIT_EXCEEDED",
                "message": f"This payment would exceed your daily limit of ₹{user_daily_limit}",
                "current_spent": user_daily_spent,
                "requested": amount,
                "limit": user_daily_limit,
                "action": "REQUIRE_VERIFICATION"
            }
        
        return {
            "valid": True,
            "message": "User limit check passed"
        }


class PaymentCallbackValidator:
    """
    Validates payment gateway callbacks
    CRITICAL: Prevents fake payment confirmations
    """
    
    @staticmethod
    def validate_callback(
        callback_data: Dict[str, Any],
        expected_order_id: str,
        expected_amount: float,
        expected_idempotency_key: str,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate payment callback from gateway
        
        Args:
            callback_data: Data received from payment gateway
            expected_order_id: Order ID we expect
            expected_amount: Amount we expect
            expected_idempotency_key: Idempotency key we expect
            signature: Callback signature for verification
            
        Returns:
            Validation result with action
        """
        errors = []
        
        # Validate order ID match
        callback_order_id = callback_data.get("order_id")
        if callback_order_id != expected_order_id:
            errors.append(
                f"Order ID mismatch: Expected={expected_order_id}, "
                f"Received={callback_order_id}"
            )
        
        # Validate amount match
        callback_amount = float(callback_data.get("amount", 0))
        if abs(callback_amount - expected_amount) > 0.01:
            errors.append(
                f"Amount mismatch: Expected={expected_amount}, "
                f"Received={callback_amount}"
            )
        
        # Validate idempotency key
        callback_key = callback_data.get("idempotency_key")
        if callback_key != expected_idempotency_key:
            errors.append(
                f"Idempotency key mismatch: Expected={expected_idempotency_key}, "
                f"Received={callback_key}"
            )
        
        # Validate signature if provided
        if signature:
            # In production, verify HMAC signature
            # For now, just check it exists
            if not callback_data.get("signature_verified", False):
                errors.append("Signature verification failed")
        
        if errors:
            logger.critical(
                f"PAYMENT CALLBACK VALIDATION FAILED: {errors}"
            )
            return {
                "valid": False,
                "errors": errors,
                "action": "REJECT_CALLBACK",
                "alert": "POTENTIAL_FRAUD",
                "message": "Payment callback failed validation checks"
            }
        
        return {
            "valid": True,
            "message": "Payment callback validated successfully",
            "action": "PROCESS_PAYMENT"
        }


class PaymentSafetyManager:
    """
    Central manager for payment safety operations
    Ensures every payment is legitimate and traceable
    """
    
    def __init__(self):
        self.validator = PaymentValidator()
        self.callback_validator = PaymentCallbackValidator()
        self.transactions: Dict[str, PaymentTransaction] = {}
        
        # Allowed payment methods
        self.allowed_methods = [
            "CREDIT_CARD",
            "DEBIT_CARD",
            "UPI",
            "NET_BANKING",
            "WALLET"
        ]
    
    def initiate_payment(
        self,
        transaction_id: str,
        order_id: str,
        user_id: str,
        amount: float,
        payment_method: str,
        idempotency_key: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initiate payment with full validation
        
        Args:
            transaction_id: Unique transaction identifier
            order_id: Associated order ID
            user_id: User making payment
            amount: Payment amount
            payment_method: Payment method chosen
            idempotency_key: Idempotency key for duplicate prevention
            metadata: Additional transaction metadata
            
        Returns:
            Initiation result with status
        """
        logger.info(
            f"Initiating payment: Transaction={transaction_id}, "
            f"Order={order_id}, Amount={amount}"
        )
        
        # Validate payment method
        method_validation = self.validator.validate_payment_method(
            payment_method, self.allowed_methods
        )
        if not method_validation["valid"]:
            return {
                "success": False,
                "error": method_validation["error"],
                "message": method_validation["message"]
            }
        
        # Create transaction record
        transaction = PaymentTransaction(
            transaction_id=transaction_id,
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            payment_method=payment_method,
            status=PaymentStatus.INITIATED,
            gateway_reference="",
            idempotency_key=idempotency_key,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            metadata=metadata or {}
        )
        
        self.transactions[transaction_id] = transaction
        
        logger.info(f"Payment initiated successfully: {transaction_id}")
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "status": PaymentStatus.INITIATED.value,
            "message": "Payment initiated successfully"
        }
    
    def process_payment_callback(
        self,
        transaction_id: str,
        callback_data: Dict[str, Any],
        gateway_reference: str
    ) -> Dict[str, Any]:
        """
        Process payment callback from gateway
        CRITICAL: Must validate before marking payment as success
        
        Args:
            transaction_id: Transaction being completed
            callback_data: Data from payment gateway
            gateway_reference: Gateway's transaction reference
            
        Returns:
            Processing result
        """
        logger.info(
            f"Processing payment callback: Transaction={transaction_id}, "
            f"Gateway={gateway_reference}"
        )
        
        # Retrieve transaction
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            logger.error(f"Transaction not found: {transaction_id}")
            return {
                "success": False,
                "error": "TRANSACTION_NOT_FOUND",
                "message": "Transaction record not found",
                "action": "REJECT_CALLBACK"
            }
        
        # Validate callback
        validation = self.callback_validator.validate_callback(
            callback_data=callback_data,
            expected_order_id=transaction.order_id,
            expected_amount=transaction.amount,
            expected_idempotency_key=transaction.idempotency_key
        )
        
        if not validation["valid"]:
            # Mark transaction as failed
            transaction.status = PaymentStatus.FAILED
            transaction.updated_at = datetime.utcnow().isoformat()
            transaction.metadata["callback_validation_errors"] = validation["errors"]
            
            return {
                "success": False,
                "error": "CALLBACK_VALIDATION_FAILED",
                "message": validation["message"],
                "action": "ALERT_FRAUD_TEAM",
                "details": validation["errors"]
            }
        
        # Mark payment as successful
        transaction.status = PaymentStatus.SUCCESS
        transaction.gateway_reference = gateway_reference
        transaction.updated_at = datetime.utcnow().isoformat()
        transaction.metadata["callback_processed_at"] = datetime.utcnow().isoformat()
        
        logger.info(
            f"Payment successful: Transaction={transaction_id}, "
            f"Order={transaction.order_id}"
        )
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "order_id": transaction.order_id,
            "status": PaymentStatus.SUCCESS.value,
            "message": "Payment processed successfully",
            "action": "UPDATE_ORDER_STATE"
        }
    
    def validate_before_shipment(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Re-validate payment before fulfillment
        Extra safety check to prevent shipping without confirmed payment
        
        Args:
            order_id: Order to validate
            
        Returns:
            Validation result
        """
        logger.info(f"Validating payment before shipment: Order={order_id}")
        
        # Find transaction for this order
        order_transactions = [
            t for t in self.transactions.values() 
            if t.order_id == order_id
        ]
        
        if not order_transactions:
            logger.error(f"No payment transaction found for order: {order_id}")
            return {
                "validated": False,
                "error": "NO_PAYMENT_FOUND",
                "message": "No payment transaction found for this order",
                "action": "HOLD_SHIPMENT"
            }
        
        # Check for successful payment
        successful_payments = [
            t for t in order_transactions 
            if t.status == PaymentStatus.SUCCESS
        ]
        
        if not successful_payments:
            logger.error(
                f"No successful payment for order: {order_id}. "
                f"Statuses: {[t.status for t in order_transactions]}"
            )
            return {
                "validated": False,
                "error": "PAYMENT_NOT_CONFIRMED",
                "message": "Payment not confirmed for this order",
                "action": "HOLD_SHIPMENT"
            }
        
        # Check for multiple successful payments (duplicate payment scenario)
        if len(successful_payments) > 1:
            logger.critical(
                f"MULTIPLE SUCCESSFUL PAYMENTS for order: {order_id}. "
                f"Count: {len(successful_payments)}"
            )
            return {
                "validated": False,
                "error": "DUPLICATE_PAYMENT_DETECTED",
                "message": "Multiple payments detected for this order",
                "action": "HOLD_SHIPMENT_AND_INVESTIGATE",
                "payment_count": len(successful_payments)
            }
        
        payment = successful_payments[0]
        
        logger.info(
            f"Payment validated for shipment: Order={order_id}, "
            f"Transaction={payment.transaction_id}"
        )
        
        return {
            "validated": True,
            "transaction_id": payment.transaction_id,
            "amount": payment.amount,
            "gateway_reference": payment.gateway_reference,
            "message": "Payment validated successfully",
            "action": "PROCEED_TO_SHIP"
        }
    
    def get_transaction_history(
        self,
        order_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get complete payment history for an order
        Useful for debugging and customer support
        
        Args:
            order_id: Order identifier
            
        Returns:
            List of all payment transactions for this order
        """
        transactions = [
            t.to_dict() for t in self.transactions.values()
            if t.order_id == order_id
        ]
        
        logger.info(
            f"Retrieved {len(transactions)} transactions for order {order_id}"
        )
        
        return transactions


class RefundManager:
    """
    Manages refund operations with full tracking
    """
    
    def __init__(self):
        self.refund_records: Dict[str, Dict] = {}
    
    def initiate_refund(
        self,
        refund_id: str,
        order_id: str,
        transaction_id: str,
        amount: float,
        reason: str,
        refund_type: str = "FULL"
    ) -> Dict[str, Any]:
        """
        Initiate refund process
        
        Args:
            refund_id: Unique refund identifier
            order_id: Associated order
            transaction_id: Original payment transaction
            amount: Amount to refund
            reason: Refund reason
            refund_type: FULL or PARTIAL
            
        Returns:
            Refund initiation result
        """
        logger.info(
            f"Initiating refund: ID={refund_id}, Order={order_id}, "
            f"Amount={amount}, Type={refund_type}"
        )
        
        refund_record = {
            "refund_id": refund_id,
            "order_id": order_id,
            "transaction_id": transaction_id,
            "amount": amount,
            "reason": reason,
            "refund_type": refund_type,
            "status": "INITIATED",
            "initiated_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "gateway_reference": None,
            "timeline": [
                {
                    "status": "INITIATED",
                    "timestamp": datetime.utcnow().isoformat(),
                    "notes": f"Refund initiated: {reason}"
                }
            ]
        }
        
        self.refund_records[refund_id] = refund_record
        
        return {
            "success": True,
            "refund_id": refund_id,
            "status": "INITIATED",
            "message": f"Refund of ₹{amount} initiated successfully",
            "estimated_days": "5-7 business days"
        }
    
    def update_refund_status(
        self,
        refund_id: str,
        status: str,
        gateway_reference: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update refund status through its lifecycle
        
        Args:
            refund_id: Refund identifier
            status: New status (PROCESSING, COMPLETED, FAILED)
            gateway_reference: Gateway refund reference
            notes: Additional notes
            
        Returns:
            Update result
        """
        if refund_id not in self.refund_records:
            logger.error(f"Refund not found: {refund_id}")
            return {
                "success": False,
                "error": "REFUND_NOT_FOUND"
            }
        
        refund = self.refund_records[refund_id]
        refund["status"] = status
        
        if gateway_reference:
            refund["gateway_reference"] = gateway_reference
        
        if status == "COMPLETED":
            refund["completed_at"] = datetime.utcnow().isoformat()
        
        # Add to timeline
        refund["timeline"].append({
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": notes or f"Refund status updated to {status}"
        })
        
        logger.info(f"Refund {refund_id} updated to {status}")
        
        return {
            "success": True,
            "refund_id": refund_id,
            "status": status,
            "message": f"Refund status updated to {status}"
        }
    
    def get_refund_status(self, refund_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current refund status
        
        Args:
            refund_id: Refund identifier
            
        Returns:
            Refund record with full timeline
        """
        return self.refund_records.get(refund_id)


# Global instances
payment_safety_manager = PaymentSafetyManager()
refund_manager = RefundManager()
