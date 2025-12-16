"""
Failure Management System - Handles All Non-Happy Paths
Member 4 Responsibility: Decision trees for every failure scenario
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from order_state_machine import (
    OrderState,
    FailureType,
    FailureDecisionTree,
    CancellationRules
)

logger = logging.getLogger(__name__)


@dataclass
class FailureContext:
    """
    Context information for failure handling
    """
    order_id: str
    user_id: str
    failure_type: FailureType
    current_state: OrderState
    timestamp: str
    details: Dict[str, Any]
    metadata: Optional[Dict] = None


@dataclass
class FailureResolution:
    """
    Resolution plan for a failure
    """
    resolution_id: str
    failure_type: FailureType
    severity: str
    recommended_actions: List[str]
    user_options: List[str]
    system_actions: List[str]
    compensation: Optional[Dict] = None
    customer_message: str = ""
    internal_notes: str = ""


class InventoryFailureHandler:
    """
    Handles all inventory-related failures
    """
    
    @staticmethod
    def handle_out_of_stock(
        order_id: str,
        product_id: str,
        quantity_requested: int,
        quantity_available: int,
        store_id: Optional[str] = None
    ) -> FailureResolution:
        """
        Handle out-of-stock scenario before payment
        
        Args:
            order_id: Order identifier
            product_id: Product that is out of stock
            quantity_requested: Quantity user wanted
            quantity_available: Current available quantity
            store_id: Store where stock was checked
            
        Returns:
            Resolution plan with alternatives
        """
        logger.warning(
            f"OUT_OF_STOCK: Order {order_id}, Product {product_id}, "
            f"Requested: {quantity_requested}, Available: {quantity_available}"
        )
        
        # System actions
        system_actions = [
            f"Block checkout for product {product_id}",
            "Query nearby stores for availability",
            "Find similar products in stock",
            "Update cart to reflect availability"
        ]
        
        # User options
        user_options = []
        if quantity_available > 0:
            user_options.append(f"Purchase available quantity ({quantity_available})")
        user_options.extend([
            "Check other store locations",
            "View similar products",
            "Join waitlist for restock notification",
            "Remove from cart"
        ])
        
        customer_message = (
            f"We're sorry, but we only have {quantity_available} units of this item available. "
            f"Would you like to purchase the available quantity, check other stores, "
            f"or explore similar products?"
        )
        
        return FailureResolution(
            resolution_id=f"RES_{order_id}_{datetime.utcnow().timestamp()}",
            failure_type=FailureType.OUT_OF_STOCK,
            severity="HIGH",
            recommended_actions=[
                "Suggest nearby store with stock",
                "Offer similar product recommendations",
                "Provide waitlist signup"
            ],
            user_options=user_options,
            system_actions=system_actions,
            customer_message=customer_message,
            internal_notes=f"Store {store_id}: Stock={quantity_available}, Requested={quantity_requested}"
        )
    
    @staticmethod
    def handle_inventory_mismatch_after_payment(
        order_id: str,
        product_id: str,
        amount_paid: float,
        product_price: float
    ) -> FailureResolution:
        """
        Handle inventory unavailable after payment was made
        CRITICAL failure - money taken but can't fulfill
        
        Args:
            order_id: Order identifier
            product_id: Product that's unavailable
            amount_paid: Amount customer paid
            product_price: Price of unavailable product
            
        Returns:
            Resolution with compensation
        """
        logger.critical(
            f"INVENTORY_MISMATCH_AFTER_PAYMENT: Order {order_id}, "
            f"Product {product_id} unavailable after payment"
        )
        
        # Calculate compensation (20% extra as goodwill)
        refund_amount = product_price
        compensation_amount = product_price * 0.20
        loyalty_points = int(product_price * 10)  # 10x points as compensation
        
        system_actions = [
            f"Lock inventory record for product {product_id}",
            "Initiate apology flow",
            "Create incident report",
            f"Auto-credit {loyalty_points} loyalty points",
            "Flag for inventory audit"
        ]
        
        user_options = [
            "Full refund + 20% compensation",
            "Wait for restock (estimated 7 days)",
            "Choose replacement product",
            "Partial refund + keep other items"
        ]
        
        compensation = {
            "type": "INVENTORY_MISMATCH",
            "refund_amount": refund_amount,
            "compensation_amount": compensation_amount,
            "loyalty_points": loyalty_points,
            "total_value": refund_amount + compensation_amount
        }
        
        customer_message = (
            f"We sincerely apologize - the item you ordered is no longer available. "
            f"We're offering a full refund of ₹{refund_amount:.2f} plus an additional "
            f"₹{compensation_amount:.2f} compensation and {loyalty_points} loyalty points. "
            f"Would you like to proceed with the refund or wait for restock?"
        )
        
        return FailureResolution(
            resolution_id=f"RES_{order_id}_{datetime.utcnow().timestamp()}",
            failure_type=FailureType.INVENTORY_MISMATCH,
            severity="CRITICAL",
            recommended_actions=[
                "Immediate full refund",
                "Apply compensation",
                "Offer replacement with priority shipping"
            ],
            user_options=user_options,
            system_actions=system_actions,
            compensation=compensation,
            customer_message=customer_message,
            internal_notes="Escalate to inventory management team for audit"
        )


class PaymentFailureHandler:
    """
    Handles all payment-related failures
    """
    
    @staticmethod
    def handle_payment_failed(
        order_id: str,
        payment_method: str,
        amount: float,
        error_code: str,
        error_message: str
    ) -> FailureResolution:
        """
        Handle payment failure scenario
        
        Args:
            order_id: Order identifier
            payment_method: Payment method that failed
            amount: Amount that was attempted
            error_code: Error code from payment gateway
            error_message: Error description
            
        Returns:
            Resolution with retry options
        """
        logger.warning(
            f"PAYMENT_FAILED: Order {order_id}, Method: {payment_method}, "
            f"Amount: {amount}, Error: {error_code}"
        )
        
        # Determine if error is retryable
        retryable_errors = ["INSUFFICIENT_FUNDS", "NETWORK_ERROR", "TIMEOUT"]
        is_retryable = any(err in error_code.upper() for err in retryable_errors)
        
        retry_window_minutes = 5
        
        system_actions = [
            "Preserve cart state",
            f"Open retry window ({retry_window_minutes} minutes)",
            "Check payment gateway status",
            "Log payment failure for analytics"
        ]
        
        user_options = ["Retry payment", "Change payment method", "Cancel order"]
        
        if not is_retryable:
            customer_message = (
                f"Payment failed: {error_message}. "
                f"Please try a different payment method or contact your bank."
            )
        else:
            customer_message = (
                f"Payment could not be processed: {error_message}. "
                f"You can retry or choose a different payment method. "
                f"Your cart will be held for {retry_window_minutes} minutes."
            )
        
        return FailureResolution(
            resolution_id=f"RES_{order_id}_{datetime.utcnow().timestamp()}",
            failure_type=FailureType.PAYMENT_FAILED,
            severity="MEDIUM",
            recommended_actions=[
                "Offer retry with same method" if is_retryable else "Suggest different payment method",
                "Preserve cart for 5 minutes",
                "Contact support if issue persists"
            ],
            user_options=user_options,
            system_actions=system_actions,
            customer_message=customer_message,
            internal_notes=f"Error Code: {error_code}, Retryable: {is_retryable}"
        )
    
    @staticmethod
    def handle_duplicate_payment(
        order_id: str,
        original_payment_id: str,
        duplicate_payment_id: str,
        amount: float
    ) -> FailureResolution:
        """
        Handle duplicate payment scenario
        Auto-trigger refund for duplicate
        
        Args:
            order_id: Order identifier
            original_payment_id: ID of original payment
            duplicate_payment_id: ID of duplicate payment
            amount: Amount paid twice
            
        Returns:
            Resolution with auto-refund plan
        """
        logger.critical(
            f"DUPLICATE_PAYMENT: Order {order_id}, "
            f"Original: {original_payment_id}, Duplicate: {duplicate_payment_id}"
        )
        
        system_actions = [
            "Block duplicate order creation",
            f"Auto-trigger refund for payment {duplicate_payment_id}",
            "Alert fraud detection system",
            "Create incident for investigation",
            "Notify customer immediately"
        ]
        
        customer_message = (
            f"We detected a duplicate payment of ₹{amount:.2f} for your order. "
            f"Don't worry - we've automatically initiated a refund which will be "
            f"processed within 5-7 business days. You will only be charged once."
        )
        
        return FailureResolution(
            resolution_id=f"RES_{order_id}_{datetime.utcnow().timestamp()}",
            failure_type=FailureType.DUPLICATE_PAYMENT,
            severity="CRITICAL",
            recommended_actions=[
                "Automatic refund of duplicate payment",
                "Keep original order intact",
                "Investigate root cause"
            ],
            user_options=[],  # No user action needed, auto-resolved
            system_actions=system_actions,
            customer_message=customer_message,
            internal_notes=f"Auto-refund triggered for {duplicate_payment_id}"
        )


class CancellationHandler:
    """
    Handles order cancellation requests
    """
    
    @staticmethod
    def handle_cancellation_request(
        order_id: str,
        user_id: str,
        current_state: OrderState,
        order_amount: float,
        reason: Optional[str] = None
    ) -> FailureResolution:
        """
        Handle order cancellation based on current state
        
        Args:
            order_id: Order identifier
            user_id: User requesting cancellation
            current_state: Current order state
            order_amount: Total order amount
            reason: Cancellation reason
            
        Returns:
            Resolution with cancellation plan
        """
        logger.info(
            f"CANCELLATION_REQUEST: Order {order_id}, State: {current_state}, "
            f"User: {user_id}, Reason: {reason}"
        )
        
        # Check if cancellation is allowed
        can_cancel = CancellationRules.can_cancel(current_state)
        cancel_action = CancellationRules.get_cancel_action(current_state)
        
        if not can_cancel:
            customer_message = (
                f"Your order is currently {current_state.value} and cannot be cancelled. "
                f"{cancel_action['description']}"
            )
            
            return FailureResolution(
                resolution_id=f"RES_{order_id}_{datetime.utcnow().timestamp()}",
                failure_type=FailureType.CANCEL_AFTER_PAYMENT,
                severity="MEDIUM",
                recommended_actions=[cancel_action["action"]],
                user_options=["Initiate return after delivery", "Contact support"],
                system_actions=["Notify user of cancellation policy"],
                customer_message=customer_message,
                internal_notes=f"Cancellation denied: State={current_state}"
            )
        
        # Process cancellation based on state
        if current_state == OrderState.CREATED:
            system_actions = ["Cancel order immediately", "Release cart hold"]
            refund_amount = 0
        elif current_state == OrderState.PAYMENT_PENDING:
            system_actions = ["Cancel payment attempt", "Release inventory hold"]
            refund_amount = 0
        else:  # PAID state
            system_actions = [
                "Initiate full refund",
                "Release inventory",
                "Update order state to CANCELLED",
                "Send confirmation email"
            ]
            refund_amount = order_amount
        
        customer_message = (
            f"Your order has been cancelled successfully. "
            f"{"A full refund of ₹" + f"{refund_amount:.2f}" + " will be processed within 5-7 business days." if refund_amount > 0 else ""}"
        )
        
        return FailureResolution(
            resolution_id=f"RES_{order_id}_{datetime.utcnow().timestamp()}",
            failure_type=FailureType.CANCEL_AFTER_PAYMENT,
            severity="HIGH" if refund_amount > 0 else "LOW",
            recommended_actions=["Process cancellation", "Refund if applicable"],
            user_options=[],
            system_actions=system_actions,
            compensation={"refund_amount": refund_amount} if refund_amount > 0 else None,
            customer_message=customer_message,
            internal_notes=f"Cancellation reason: {reason}"
        )


class AddressFailureHandler:
    """
    Handles address and delivery-related failures
    """
    
    @staticmethod
    def handle_address_error(
        order_id: str,
        address_type: str,
        error_reason: str,
        pincode: Optional[str] = None
    ) -> FailureResolution:
        """
        Handle invalid or unserviceable address
        
        Args:
            order_id: Order identifier
            address_type: Type of address error
            error_reason: Description of error
            pincode: Pincode that failed validation
            
        Returns:
            Resolution with address correction flow
        """
        logger.warning(
            f"ADDRESS_ERROR: Order {order_id}, Type: {address_type}, "
            f"Reason: {error_reason}, Pincode: {pincode}"
        )
        
        system_actions = [
            "Hold fulfillment",
            "Validate pincode against serviceable areas",
            "Suggest nearest serviceable location",
            "Set 48-hour correction deadline"
        ]
        
        user_options = [
            "Correct address",
            "Change delivery location",
            "Choose pickup from store",
            "Cancel order"
        ]
        
        customer_message = (
            f"There's an issue with your delivery address: {error_reason}. "
            f"Please update your address or choose an alternate delivery location. "
            f"Your order is on hold and will be cancelled if not corrected within 48 hours."
        )
        
        return FailureResolution(
            resolution_id=f"RES_{order_id}_{datetime.utcnow().timestamp()}",
            failure_type=FailureType.ADDRESS_ERROR,
            severity="MEDIUM",
            recommended_actions=[
                "Prompt address correction",
                "Hold fulfillment",
                "Auto-cancel if not fixed in 48 hours"
            ],
            user_options=user_options,
            system_actions=system_actions,
            customer_message=customer_message,
            internal_notes=f"Pincode: {pincode}, Error: {error_reason}"
        )
    
    @staticmethod
    def handle_delivery_failed(
        order_id: str,
        attempt_number: int,
        failure_reason: str,
        delivery_partner: str
    ) -> FailureResolution:
        """
        Handle failed delivery attempt
        
        Args:
            order_id: Order identifier
            attempt_number: Which delivery attempt failed
            failure_reason: Why delivery failed
            delivery_partner: Delivery partner name
            
        Returns:
            Resolution with reattempt plan
        """
        max_attempts = 3
        remaining_attempts = max_attempts - attempt_number
        
        logger.warning(
            f"DELIVERY_FAILED: Order {order_id}, Attempt: {attempt_number}/{max_attempts}, "
            f"Reason: {failure_reason}, Partner: {delivery_partner}"
        )
        
        if remaining_attempts > 0:
            system_actions = [
                f"Schedule reattempt ({remaining_attempts} remaining)",
                "Contact customer for availability",
                "Update delivery status"
            ]
            
            user_options = [
                "Reschedule delivery",
                "Change delivery address",
                "Pickup from hub",
                "Cancel and refund"
            ]
            
            customer_message = (
                f"Delivery attempt {attempt_number} failed: {failure_reason}. "
                f"We will attempt delivery {remaining_attempts} more time(s). "
                f"Would you like to reschedule or update your delivery preferences?"
            )
        else:
            system_actions = [
                "Return to warehouse",
                "Initiate automatic refund",
                "Close delivery ticket"
            ]
            
            user_options = ["Accept refund", "Arrange pickup from warehouse"]
            
            customer_message = (
                f"We were unable to deliver your order after {max_attempts} attempts. "
                f"Your order is being returned to our warehouse and a full refund "
                f"will be processed. You can also arrange to pick up from our warehouse."
            )
        
        return FailureResolution(
            resolution_id=f"RES_{order_id}_{datetime.utcnow().timestamp()}",
            failure_type=FailureType.DELIVERY_FAILED,
            severity="HIGH" if remaining_attempts == 0 else "MEDIUM",
            recommended_actions=[
                "Reattempt delivery" if remaining_attempts > 0 else "Process refund",
                "Contact customer",
                "Update tracking"
            ],
            user_options=user_options,
            system_actions=system_actions,
            customer_message=customer_message,
            internal_notes=f"Attempt {attempt_number}/{max_attempts}, Partner: {delivery_partner}"
        )


class FailureOrchestrator:
    """
    Central orchestrator for all failure handling
    Routes failures to appropriate handlers
    """
    
    def __init__(self):
        self.inventory_handler = InventoryFailureHandler()
        self.payment_handler = PaymentFailureHandler()
        self.cancellation_handler = CancellationHandler()
        self.address_handler = AddressFailureHandler()
    
    def handle_failure(self, context: FailureContext) -> FailureResolution:
        """
        Route failure to appropriate handler
        
        Args:
            context: Failure context information
            
        Returns:
            Resolution plan
        """
        logger.info(
            f"Handling failure: {context.failure_type} for order {context.order_id}"
        )
        
        if context.failure_type == FailureType.OUT_OF_STOCK:
            return self.inventory_handler.handle_out_of_stock(**context.details)
        
        elif context.failure_type == FailureType.INVENTORY_MISMATCH:
            return self.inventory_handler.handle_inventory_mismatch_after_payment(
                **context.details
            )
        
        elif context.failure_type == FailureType.PAYMENT_FAILED:
            return self.payment_handler.handle_payment_failed(**context.details)
        
        elif context.failure_type == FailureType.DUPLICATE_PAYMENT:
            return self.payment_handler.handle_duplicate_payment(**context.details)
        
        elif context.failure_type == FailureType.CANCEL_AFTER_PAYMENT:
            return self.cancellation_handler.handle_cancellation_request(
                **context.details
            )
        
        elif context.failure_type == FailureType.ADDRESS_ERROR:
            return self.address_handler.handle_address_error(**context.details)
        
        elif context.failure_type == FailureType.DELIVERY_FAILED:
            return self.address_handler.handle_delivery_failed(**context.details)
        
        else:
            logger.error(f"Unknown failure type: {context.failure_type}")
            return FailureResolution(
                resolution_id=f"RES_{context.order_id}_{datetime.utcnow().timestamp()}",
                failure_type=context.failure_type,
                severity="UNKNOWN",
                recommended_actions=["Contact support"],
                user_options=["Contact support", "Retry"],
                system_actions=["Log error", "Alert engineering team"],
                customer_message="An unexpected error occurred. Please contact support."
            )


# Global failure orchestrator instance
failure_orchestrator = FailureOrchestrator()
