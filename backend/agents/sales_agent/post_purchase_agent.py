"""
Post-Purchase Agent - User Trust After Order Placement
Member 4 Responsibility: Everything after money is paid

Handles:
- Order tracking
- Return initiation
- Exchange logic
- Refund lifecycle
- Feedback & rating
- Loyalty disputes
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from order_state_machine import OrderState

logger = logging.getLogger(__name__)


class ReturnReason(str, Enum):
    """Reasons for product return"""
    DEFECTIVE = "DEFECTIVE"
    WRONG_ITEM = "WRONG_ITEM"
    SIZE_FIT_ISSUE = "SIZE_FIT_ISSUE"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    DAMAGED_IN_TRANSIT = "DAMAGED_IN_TRANSIT"
    CHANGED_MIND = "CHANGED_MIND"
    BETTER_PRICE_ELSEWHERE = "BETTER_PRICE_ELSEWHERE"
    OTHER = "OTHER"


class ExchangeType(str, Enum):
    """Types of exchange"""
    SIZE_EXCHANGE = "SIZE_EXCHANGE"
    COLOR_EXCHANGE = "COLOR_EXCHANGE"
    PRODUCT_EXCHANGE = "PRODUCT_EXCHANGE"


@dataclass
class OrderTracking:
    """Order tracking information"""
    order_id: str
    current_state: OrderState
    tracking_number: Optional[str]
    carrier: Optional[str]
    estimated_delivery: Optional[str]
    tracking_updates: List[Dict[str, str]]
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "current_state": self.current_state.value,
            "tracking_number": self.tracking_number,
            "carrier": self.carrier,
            "estimated_delivery": self.estimated_delivery,
            "tracking_updates": self.tracking_updates
        }


@dataclass
class ReturnRequest:
    """Return request details"""
    return_id: str
    order_id: str
    user_id: str
    product_ids: List[str]
    reason: ReturnReason
    reason_details: str
    requested_at: str
    status: str  # REQUESTED, APPROVED, PICKUP_SCHEDULED, RECEIVED, REFUNDED
    pickup_date: Optional[str]
    refund_amount: float
    images: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "return_id": self.return_id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "product_ids": self.product_ids,
            "reason": self.reason.value,
            "reason_details": self.reason_details,
            "requested_at": self.requested_at,
            "status": self.status,
            "pickup_date": self.pickup_date,
            "refund_amount": self.refund_amount,
            "images": self.images
        }


@dataclass
class ExchangeRequest:
    """Exchange request details"""
    exchange_id: str
    order_id: str
    user_id: str
    original_product_id: str
    requested_product_id: str
    exchange_type: ExchangeType
    reason: str
    requested_at: str
    status: str  # REQUESTED, APPROVED, PICKUP_SCHEDULED, RECEIVED, DISPATCHED
    price_difference: float
    
    def to_dict(self) -> Dict:
        return {
            "exchange_id": self.exchange_id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "original_product_id": self.original_product_id,
            "requested_product_id": self.requested_product_id,
            "exchange_type": self.exchange_type.value,
            "reason": self.reason,
            "requested_at": self.requested_at,
            "status": self.status,
            "price_difference": self.price_difference
        }


class OrderTrackingManager:
    """
    Manages order tracking and status updates
    """
    
    def __init__(self):
        self.tracking_records: Dict[str, OrderTracking] = {}
    
    def create_tracking(
        self,
        order_id: str,
        initial_state: OrderState,
        tracking_number: Optional[str] = None,
        carrier: Optional[str] = None,
        estimated_delivery: Optional[str] = None
    ) -> OrderTracking:
        """
        Create tracking record for order
        
        Args:
            order_id: Order identifier
            initial_state: Initial order state
            tracking_number: Shipping tracking number
            carrier: Delivery carrier name
            estimated_delivery: Estimated delivery date
            
        Returns:
            Created tracking record
        """
        tracking = OrderTracking(
            order_id=order_id,
            current_state=initial_state,
            tracking_number=tracking_number,
            carrier=carrier,
            estimated_delivery=estimated_delivery,
            tracking_updates=[{
                "status": initial_state.value,
                "timestamp": datetime.utcnow().isoformat(),
                "description": f"Order {initial_state.value.lower()}"
            }]
        )
        
        self.tracking_records[order_id] = tracking
        
        logger.info(f"Created tracking for order {order_id}")
        
        return tracking
    
    def update_tracking(
        self,
        order_id: str,
        new_state: OrderState,
        description: str,
        location: Optional[str] = None
    ) -> bool:
        """
        Add tracking update
        
        Args:
            order_id: Order identifier
            new_state: New order state
            description: Update description
            location: Current location (for transit updates)
            
        Returns:
            True if updated successfully
        """
        if order_id not in self.tracking_records:
            logger.error(f"Tracking record not found for order: {order_id}")
            return False
        
        tracking = self.tracking_records[order_id]
        tracking.current_state = new_state
        
        update = {
            "status": new_state.value,
            "timestamp": datetime.utcnow().isoformat(),
            "description": description
        }
        
        if location:
            update["location"] = location
        
        tracking.tracking_updates.append(update)
        
        logger.info(f"Updated tracking for order {order_id}: {description}")
        
        return True
    
    def get_tracking_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tracking information for customer
        
        Args:
            order_id: Order identifier
            
        Returns:
            Customer-facing tracking information
        """
        if order_id not in self.tracking_records:
            return None
        
        tracking = self.tracking_records[order_id]
        
        return {
            "order_id": order_id,
            "current_status": tracking.current_state.value,
            "tracking_number": tracking.tracking_number,
            "carrier": tracking.carrier,
            "estimated_delivery": tracking.estimated_delivery,
            "updates": tracking.tracking_updates,
            "last_updated": tracking.tracking_updates[-1]["timestamp"] if tracking.tracking_updates else None
        }


class ReturnManager:
    """
    Manages product returns
    """
    
    def __init__(self):
        self.return_requests: Dict[str, ReturnRequest] = {}
        self.return_window_days = 30  # 30-day return window
    
    def check_return_eligibility(
        self,
        order_id: str,
        order_date: str,
        order_state: OrderState,
        product_category: str
    ) -> Dict[str, Any]:
        """
        Check if order is eligible for return
        
        Args:
            order_id: Order identifier
            order_date: When order was placed
            order_state: Current order state
            product_category: Product category (some may be non-returnable)
            
        Returns:
            Eligibility result
        """
        # Check state
        if order_state != OrderState.DELIVERED:
            return {
                "eligible": False,
                "reason": "Order must be delivered to initiate return",
                "current_state": order_state.value
            }
        
        # Check return window
        order_datetime = datetime.fromisoformat(order_date)
        days_since_order = (datetime.utcnow() - order_datetime).days
        
        if days_since_order > self.return_window_days:
            return {
                "eligible": False,
                "reason": f"Return window ({self.return_window_days} days) has expired",
                "days_since_order": days_since_order,
                "return_window": self.return_window_days
            }
        
        # Check non-returnable categories
        non_returnable = ["UNDERWEAR", "INTIMATE", "GIFT_CARD", "PERISHABLE"]
        if product_category in non_returnable:
            return {
                "eligible": False,
                "reason": f"Product category '{product_category}' is not eligible for return",
                "category": product_category
            }
        
        days_remaining = self.return_window_days - days_since_order
        
        return {
            "eligible": True,
            "return_window_remaining": f"{days_remaining} days",
            "message": f"You can return this order within the next {days_remaining} days"
        }
    
    def initiate_return(
        self,
        return_id: str,
        order_id: str,
        user_id: str,
        product_ids: List[str],
        reason: ReturnReason,
        reason_details: str,
        refund_amount: float,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Initiate return request
        
        Args:
            return_id: Unique return identifier
            order_id: Order being returned
            user_id: User requesting return
            product_ids: Products to return
            reason: Return reason
            reason_details: Detailed explanation
            refund_amount: Amount to refund
            images: Optional images of product/issue
            
        Returns:
            Return initiation result
        """
        logger.info(
            f"Initiating return: Return={return_id}, Order={order_id}, "
            f"Reason={reason.value}"
        )
        
        return_request = ReturnRequest(
            return_id=return_id,
            order_id=order_id,
            user_id=user_id,
            product_ids=product_ids,
            reason=reason,
            reason_details=reason_details,
            requested_at=datetime.utcnow().isoformat(),
            status="REQUESTED",
            pickup_date=None,
            refund_amount=refund_amount,
            images=images or []
        )
        
        self.return_requests[return_id] = return_request
        
        # Calculate pickup date (2 days from now)
        pickup_date = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        return {
            "success": True,
            "return_id": return_id,
            "status": "REQUESTED",
            "pickup_date": pickup_date,
            "refund_amount": refund_amount,
            "message": (
                f"Return request submitted successfully. Pickup scheduled for {pickup_date}. "
                f"Refund of ₹{refund_amount} will be processed after item inspection."
            ),
            "next_steps": [
                "Pack the item in original packaging",
                "Keep all tags and accessories",
                "Our courier will pick up on the scheduled date",
                "Refund will be processed within 5-7 days after receipt"
            ]
        }
    
    def update_return_status(
        self,
        return_id: str,
        new_status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update return request status
        
        Args:
            return_id: Return identifier
            new_status: New status
            notes: Additional notes
            
        Returns:
            True if updated successfully
        """
        if return_id not in self.return_requests:
            logger.error(f"Return request not found: {return_id}")
            return False
        
        return_request = self.return_requests[return_id]
        return_request.status = new_status
        
        logger.info(
            f"Return {return_id} updated to {new_status}"
            f"{': ' + notes if notes else ''}"
        )
        
        return True
    
    def get_return_status(self, return_id: str) -> Optional[Dict[str, Any]]:
        """
        Get return status for customer
        
        Args:
            return_id: Return identifier
            
        Returns:
            Return status information
        """
        if return_id not in self.return_requests:
            return None
        
        return_request = self.return_requests[return_id]
        
        status_messages = {
            "REQUESTED": "Return request received and under review",
            "APPROVED": "Return approved. Pickup will be scheduled shortly.",
            "PICKUP_SCHEDULED": f"Pickup scheduled for {return_request.pickup_date}",
            "RECEIVED": "Item received at warehouse. Inspection in progress.",
            "REFUNDED": f"Refund of ₹{return_request.refund_amount} processed successfully"
        }
        
        return {
            "return_id": return_id,
            "order_id": return_request.order_id,
            "status": return_request.status,
            "status_message": status_messages.get(return_request.status, "Processing"),
            "refund_amount": return_request.refund_amount,
            "requested_at": return_request.requested_at,
            "pickup_date": return_request.pickup_date
        }


class ExchangeManager:
    """
    Manages product exchanges
    """
    
    def __init__(self):
        self.exchange_requests: Dict[str, ExchangeRequest] = {}
    
    def initiate_exchange(
        self,
        exchange_id: str,
        order_id: str,
        user_id: str,
        original_product_id: str,
        requested_product_id: str,
        exchange_type: ExchangeType,
        reason: str,
        original_price: float,
        new_price: float
    ) -> Dict[str, Any]:
        """
        Initiate exchange request
        
        Args:
            exchange_id: Unique exchange identifier
            order_id: Original order ID
            user_id: User requesting exchange
            original_product_id: Product to exchange
            requested_product_id: Desired replacement product
            exchange_type: Type of exchange
            reason: Exchange reason
            original_price: Price of original product
            new_price: Price of new product
            
        Returns:
            Exchange initiation result
        """
        logger.info(
            f"Initiating exchange: Exchange={exchange_id}, Order={order_id}, "
            f"Type={exchange_type.value}"
        )
        
        price_difference = new_price - original_price
        
        exchange_request = ExchangeRequest(
            exchange_id=exchange_id,
            order_id=order_id,
            user_id=user_id,
            original_product_id=original_product_id,
            requested_product_id=requested_product_id,
            exchange_type=exchange_type,
            reason=reason,
            requested_at=datetime.utcnow().isoformat(),
            status="REQUESTED",
            price_difference=price_difference
        )
        
        self.exchange_requests[exchange_id] = exchange_request
        
        # Build response message
        if price_difference > 0:
            payment_message = f"You'll need to pay an additional ₹{price_difference:.2f}"
        elif price_difference < 0:
            payment_message = f"₹{abs(price_difference):.2f} will be refunded to your account"
        else:
            payment_message = "No price difference"
        
        return {
            "success": True,
            "exchange_id": exchange_id,
            "status": "REQUESTED",
            "price_difference": price_difference,
            "message": (
                f"Exchange request submitted successfully. {payment_message}. "
                f"Pickup for the original item will be scheduled within 2 days."
            ),
            "next_steps": [
                "Pack original item with all tags and accessories",
                "Our courier will pick up the item",
                "New item will be dispatched after receiving original",
                "Additional payment will be collected during delivery" if price_difference > 0 else None
            ]
        }
    
    def get_exchange_status(self, exchange_id: str) -> Optional[Dict[str, Any]]:
        """
        Get exchange status
        
        Args:
            exchange_id: Exchange identifier
            
        Returns:
            Exchange status information
        """
        if exchange_id not in self.exchange_requests:
            return None
        
        exchange = self.exchange_requests[exchange_id]
        
        status_messages = {
            "REQUESTED": "Exchange request received and under review",
            "APPROVED": "Exchange approved. Pickup will be scheduled shortly.",
            "PICKUP_SCHEDULED": "Pickup scheduled for original item",
            "RECEIVED": "Original item received. New item will be dispatched soon.",
            "DISPATCHED": "New item dispatched. You'll receive it within 3-5 days."
        }
        
        return {
            "exchange_id": exchange_id,
            "order_id": exchange.order_id,
            "status": exchange.status,
            "status_message": status_messages.get(exchange.status, "Processing"),
            "exchange_type": exchange.exchange_type.value,
            "price_difference": exchange.price_difference,
            "requested_at": exchange.requested_at
        }


class FeedbackManager:
    """
    Manages customer feedback and ratings
    """
    
    def __init__(self):
        self.feedback_records: Dict[str, Dict] = {}
    
    def submit_feedback(
        self,
        feedback_id: str,
        order_id: str,
        user_id: str,
        rating: int,
        product_ratings: Dict[str, int],
        review: str,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Submit order feedback
        
        Args:
            feedback_id: Unique feedback identifier
            order_id: Order being reviewed
            user_id: User submitting feedback
            rating: Overall rating (1-5)
            product_ratings: Individual product ratings
            review: Written review
            images: Optional review images
            
        Returns:
            Submission result
        """
        if not (1 <= rating <= 5):
            return {
                "success": False,
                "error": "Invalid rating. Must be between 1 and 5."
            }
        
        feedback = {
            "feedback_id": feedback_id,
            "order_id": order_id,
            "user_id": user_id,
            "rating": rating,
            "product_ratings": product_ratings,
            "review": review,
            "images": images or [],
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "SUBMITTED",
            "helpful_count": 0
        }
        
        self.feedback_records[feedback_id] = feedback
        
        # Calculate loyalty points reward (base 10 + bonus for good reviews)
        loyalty_points = 10
        if rating >= 4 and len(review) > 50:
            loyalty_points = 50  # Bonus for detailed positive review
        
        logger.info(
            f"Feedback submitted: ID={feedback_id}, Order={order_id}, "
            f"Rating={rating}/5"
        )
        
        return {
            "success": True,
            "feedback_id": feedback_id,
            "loyalty_points_earned": loyalty_points,
            "message": (
                f"Thank you for your feedback! "
                f"You've earned {loyalty_points} loyalty points."
            )
        }


class PostPurchaseAgent:
    """
    Central agent for all post-purchase operations
    """
    
    def __init__(self):
        self.tracking_manager = OrderTrackingManager()
        self.return_manager = ReturnManager()
        self.exchange_manager = ExchangeManager()
        self.feedback_manager = FeedbackManager()
    
    def handle_query(
        self,
        query_type: str,
        query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route post-purchase queries to appropriate manager
        
        Args:
            query_type: Type of query (tracking, return, exchange, feedback)
            query_data: Query parameters
            
        Returns:
            Query response
        """
        logger.info(f"Handling post-purchase query: {query_type}")
        
        if query_type == "track_order":
            order_id = query_data.get("order_id")
            tracking_info = self.tracking_manager.get_tracking_info(order_id)
            
            if not tracking_info:
                return {
                    "success": False,
                    "error": "Order not found",
                    "message": "No tracking information available for this order"
                }
            
            return {
                "success": True,
                "tracking": tracking_info
            }
        
        elif query_type == "initiate_return":
            return self.return_manager.initiate_return(**query_data)
        
        elif query_type == "return_status":
            return_id = query_data.get("return_id")
            status = self.return_manager.get_return_status(return_id)
            
            if not status:
                return {
                    "success": False,
                    "error": "Return request not found"
                }
            
            return {
                "success": True,
                "return": status
            }
        
        elif query_type == "initiate_exchange":
            return self.exchange_manager.initiate_exchange(**query_data)
        
        elif query_type == "exchange_status":
            exchange_id = query_data.get("exchange_id")
            status = self.exchange_manager.get_exchange_status(exchange_id)
            
            if not status:
                return {
                    "success": False,
                    "error": "Exchange request not found"
                }
            
            return {
                "success": True,
                "exchange": status
            }
        
        elif query_type == "submit_feedback":
            return self.feedback_manager.submit_feedback(**query_data)
        
        else:
            return {
                "success": False,
                "error": "Unknown query type",
                "message": f"Query type '{query_type}' is not supported"
            }


# Global post-purchase agent instance
post_purchase_agent = PostPurchaseAgent()
