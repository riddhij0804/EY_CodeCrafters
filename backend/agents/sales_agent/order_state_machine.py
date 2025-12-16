"""
Order State Machine - Foundation for Transaction Trust
Member 4 Responsibility: State management and transition validation
"""
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OrderState(str, Enum):
    """
    Complete order lifecycle states
    Every order MUST be in exactly one of these states
    """
    CREATED = "CREATED"  # Cart exists, no payment attempt
    PAYMENT_PENDING = "PAYMENT_PENDING"  # Payment initiated, awaiting confirmation
    PAID = "PAID"  # Payment successful, awaiting fulfillment
    PACKED = "PACKED"  # Order packed, ready to ship
    SHIPPED = "SHIPPED"  # Order in transit
    DELIVERED = "DELIVERED"  # Order delivered successfully
    CANCELLED = "CANCELLED"  # Order cancelled before shipment
    RETURN_REQUESTED = "RETURN_REQUESTED"  # User requested return
    RETURNED = "RETURNED"  # Item returned to warehouse
    REFUNDED = "REFUNDED"  # Money refunded to customer


class RefundState(str, Enum):
    """
    Refund lifecycle states
    Never mark order as REFUNDED until refund is COMPLETED
    """
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FailureType(str, Enum):
    """
    All possible failure scenarios Member 4 must handle
    """
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    INVENTORY_MISMATCH = "INVENTORY_MISMATCH"
    CANCEL_AFTER_PAYMENT = "CANCEL_AFTER_PAYMENT"
    ADDRESS_ERROR = "ADDRESS_ERROR"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class StateTransition:
    """
    Defines valid state transitions and their rules
    """
    
    # Valid state transition map
    VALID_TRANSITIONS: Dict[OrderState, List[OrderState]] = {
        OrderState.CREATED: [OrderState.PAYMENT_PENDING, OrderState.CANCELLED],
        OrderState.PAYMENT_PENDING: [OrderState.PAID, OrderState.CANCELLED, OrderState.CREATED],
        OrderState.PAID: [OrderState.PACKED, OrderState.CANCELLED, OrderState.REFUNDED],
        OrderState.PACKED: [OrderState.SHIPPED, OrderState.RETURN_REQUESTED],
        OrderState.SHIPPED: [OrderState.DELIVERED, OrderState.RETURN_REQUESTED],
        OrderState.DELIVERED: [OrderState.RETURN_REQUESTED],
        OrderState.CANCELLED: [],  # Terminal state
        OrderState.RETURN_REQUESTED: [OrderState.RETURNED, OrderState.DELIVERED],
        OrderState.RETURNED: [OrderState.REFUNDED],
        OrderState.REFUNDED: [],  # Terminal state
    }
    
    @classmethod
    def is_valid_transition(cls, from_state: OrderState, to_state: OrderState) -> bool:
        """
        Validate if state transition is allowed
        
        Args:
            from_state: Current order state
            to_state: Desired new state
            
        Returns:
            True if transition is valid, False otherwise
        """
        if from_state not in cls.VALID_TRANSITIONS:
            logger.error(f"Unknown from_state: {from_state}")
            return False
        
        allowed_states = cls.VALID_TRANSITIONS[from_state]
        is_valid = to_state in allowed_states
        
        if not is_valid:
            logger.warning(
                f"Invalid state transition attempted: {from_state} -> {to_state}. "
                f"Allowed transitions: {allowed_states}"
            )
        
        return is_valid
    
    @classmethod
    def get_allowed_transitions(cls, current_state: OrderState) -> List[OrderState]:
        """
        Get list of allowed next states from current state
        
        Args:
            current_state: Current order state
            
        Returns:
            List of allowed next states
        """
        return cls.VALID_TRANSITIONS.get(current_state, [])
    
    @classmethod
    def is_terminal_state(cls, state: OrderState) -> bool:
        """
        Check if state is terminal (no further transitions possible)
        
        Args:
            state: State to check
            
        Returns:
            True if terminal state, False otherwise
        """
        return len(cls.VALID_TRANSITIONS.get(state, [])) == 0


class CancellationRules:
    """
    Rules for when cancellation is allowed and what action to take
    """
    
    @staticmethod
    def can_cancel(order_state: OrderState) -> bool:
        """
        Determine if order can be cancelled based on current state
        
        Args:
            order_state: Current order state
            
        Returns:
            True if cancellation is allowed
        """
        cancellable_states = [
            OrderState.CREATED,
            OrderState.PAYMENT_PENDING,
            OrderState.PAID
        ]
        return order_state in cancellable_states
    
    @staticmethod
    def get_cancel_action(order_state: OrderState) -> Dict[str, str]:
        """
        Get appropriate action when cancellation is requested
        
        Args:
            order_state: Current order state
            
        Returns:
            Dictionary with action type and description
        """
        actions = {
            OrderState.CREATED: {
                "action": "CANCEL",
                "description": "Cancel order immediately, no refund needed"
            },
            OrderState.PAYMENT_PENDING: {
                "action": "CANCEL",
                "description": "Cancel payment attempt, mark order cancelled"
            },
            OrderState.PAID: {
                "action": "FULL_REFUND",
                "description": "Cancel order and initiate full refund"
            },
            OrderState.PACKED: {
                "action": "EXCHANGE_ONLY",
                "description": "Cannot cancel, only exchange available"
            },
            OrderState.SHIPPED: {
                "action": "RETURN_FLOW",
                "description": "Cannot cancel, initiate return flow"
            },
            OrderState.DELIVERED: {
                "action": "RETURN_FLOW",
                "description": "Cannot cancel, initiate return flow"
            }
        }
        return actions.get(order_state, {
            "action": "NOT_ALLOWED",
            "description": "Cancellation not allowed in this state"
        })


class FailureDecisionTree:
    """
    Decision tree for handling each failure type
    """
    
    @staticmethod
    def get_failure_actions(failure_type: FailureType, context: Dict) -> Dict:
        """
        Get recommended actions for a specific failure type
        
        Args:
            failure_type: Type of failure encountered
            context: Additional context (order details, inventory, etc.)
            
        Returns:
            Dictionary with recommended actions and options
        """
        if failure_type == FailureType.OUT_OF_STOCK:
            return {
                "severity": "HIGH",
                "actions": [
                    "Check nearby store availability",
                    "Suggest similar products",
                    "Offer waitlist registration",
                    "Block checkout for this SKU"
                ],
                "user_options": ["alternate_store", "similar_product", "waitlist", "cancel"],
                "system_action": "BLOCK_CHECKOUT"
            }
        
        elif failure_type == FailureType.INVENTORY_MISMATCH:
            return {
                "severity": "CRITICAL",
                "actions": [
                    "Lock affected inventory",
                    "Initiate apology flow",
                    "Offer partial refund",
                    "Provide replacement options",
                    "Auto-apply loyalty compensation"
                ],
                "user_options": ["partial_refund", "replacement", "wait_restock", "full_refund"],
                "system_action": "LOCK_INVENTORY"
            }
        
        elif failure_type == FailureType.PAYMENT_FAILED:
            return {
                "severity": "MEDIUM",
                "actions": [
                    "Open retry window (5 minutes)",
                    "Suggest alternative payment method",
                    "Check payment gateway status",
                    "Preserve cart state"
                ],
                "user_options": ["retry", "change_payment_method", "cancel"],
                "system_action": "HOLD_CART"
            }
        
        elif failure_type == FailureType.DUPLICATE_PAYMENT:
            return {
                "severity": "CRITICAL",
                "actions": [
                    "Validate idempotency key",
                    "Block duplicate order creation",
                    "Auto-trigger refund for duplicate",
                    "Alert fraud detection system"
                ],
                "user_options": [],
                "system_action": "AUTO_REFUND"
            }
        
        elif failure_type == FailureType.CANCEL_AFTER_PAYMENT:
            return {
                "severity": "HIGH",
                "actions": [
                    "Check fulfillment state",
                    "If not shipped: instant cancel + refund",
                    "If shipped: convert to return flow",
                    "Update inventory immediately"
                ],
                "user_options": ["confirm_cancel"],
                "system_action": "CHECK_FULFILLMENT_STATE"
            }
        
        elif failure_type == FailureType.ADDRESS_ERROR:
            return {
                "severity": "MEDIUM",
                "actions": [
                    "Validate pincode",
                    "Offer address correction",
                    "Hold fulfillment until fixed",
                    "Suggest alternate delivery location"
                ],
                "user_options": ["correct_address", "change_location"],
                "system_action": "HOLD_FULFILLMENT"
            }
        
        elif failure_type == FailureType.DELIVERY_FAILED:
            return {
                "severity": "HIGH",
                "actions": [
                    "Reattempt delivery (3 attempts max)",
                    "Contact customer for availability",
                    "Offer alternate delivery slot",
                    "Return to warehouse if all attempts fail"
                ],
                "user_options": ["reschedule", "change_address", "pickup"],
                "system_action": "REATTEMPT_DELIVERY"
            }
        
        else:  # SYSTEM_ERROR
            return {
                "severity": "CRITICAL",
                "actions": [
                    "Log error details",
                    "Rollback partial transaction",
                    "Alert engineering team",
                    "Provide user with incident ID"
                ],
                "user_options": ["retry_later", "contact_support"],
                "system_action": "ROLLBACK"
            }


class StateTransitionLogger:
    """
    Audit logging for all state transitions
    Critical for debugging and compliance
    """
    
    @staticmethod
    def log_transition(
        order_id: str,
        from_state: OrderState,
        to_state: OrderState,
        triggered_by: str,
        reason: str,
        metadata: Optional[Dict] = None
    ):
        """
        Log state transition with full audit trail
        
        Args:
            order_id: Order identifier
            from_state: Previous state
            to_state: New state
            triggered_by: User/system that triggered transition
            reason: Reason for transition
            metadata: Additional context
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "order_id": order_id,
            "transition": f"{from_state} -> {to_state}",
            "triggered_by": triggered_by,
            "reason": reason,
            "metadata": metadata or {}
        }
        
        logger.info(f"STATE_TRANSITION: {log_entry}")
        
        # In production, this would write to:
        # - Database audit table
        # - Elasticsearch for search
        # - Data warehouse for analytics
        return log_entry
