"""
Member 4 Comprehensive Test Suite
Tests all production-safety features
"""
import unittest
import uuid
from datetime import datetime

from order_state_machine import (
    OrderState, StateTransition, CancellationRules,
    FailureType, FailureDecisionTree
)
from idempotency_manager import (
    idempotency_manager, payment_validator
)
from failure_management import (
    failure_orchestrator, FailureContext,
    InventoryFailureHandler, PaymentFailureHandler
)
from payment_safety import (
    payment_safety_manager, refund_manager,
    PaymentStatus, PaymentValidator
)
from post_purchase_agent import (
    post_purchase_agent, ReturnReason, ExchangeType
)
from transaction_trust import (
    retry_executor, transaction_manager,
    audit_logger, RetryPolicy
)


class TestOrderStateMachine(unittest.TestCase):
    """Test order state machine and transitions"""
    
    def test_valid_transitions(self):
        """Test valid state transitions"""
        self.assertTrue(
            StateTransition.is_valid_transition(
                OrderState.CREATED, OrderState.PAYMENT_PENDING
            )
        )
        self.assertTrue(
            StateTransition.is_valid_transition(
                OrderState.PAID, OrderState.PACKED
            )
        )
        self.assertTrue(
            StateTransition.is_valid_transition(
                OrderState.SHIPPED, OrderState.DELIVERED
            )
        )
    
    def test_invalid_transitions(self):
        """Test invalid state transitions"""
        self.assertFalse(
            StateTransition.is_valid_transition(
                OrderState.CREATED, OrderState.SHIPPED
            )
        )
        self.assertFalse(
            StateTransition.is_valid_transition(
                OrderState.CANCELLED, OrderState.PAID
            )
        )
    
    def test_cancellation_rules(self):
        """Test cancellation rules by state"""
        # Can cancel in PAID state
        self.assertTrue(CancellationRules.can_cancel(OrderState.PAID))
        
        # Cannot cancel in SHIPPED state
        self.assertFalse(CancellationRules.can_cancel(OrderState.SHIPPED))
        
        # Check cancel action
        action = CancellationRules.get_cancel_action(OrderState.PAID)
        self.assertEqual(action["action"], "FULL_REFUND")
    
    def test_terminal_states(self):
        """Test terminal state detection"""
        self.assertTrue(StateTransition.is_terminal_state(OrderState.CANCELLED))
        self.assertTrue(StateTransition.is_terminal_state(OrderState.REFUNDED))
        self.assertFalse(StateTransition.is_terminal_state(OrderState.PAID))


class TestIdempotencyManager(unittest.TestCase):
    """Test idempotency and duplicate prevention"""
    
    def test_idempotency_key_generation(self):
        """Test idempotency key generation"""
        key1 = idempotency_manager.generate_key(
            user_id="user_001",
            operation_type="payment",
            data={"order_id": "ORD_123", "amount": 100.0}
        )
        
        key2 = idempotency_manager.generate_key(
            user_id="user_001",
            operation_type="payment",
            data={"order_id": "ORD_123", "amount": 100.0}
        )
        
        # Same data should generate same key
        self.assertEqual(key1, key2)
    
    def test_duplicate_detection(self):
        """Test duplicate operation detection"""
        order_id = f"ORD_{uuid.uuid4().hex[:8]}"
        request_data = {"order_id": order_id, "amount": 100.0}
        
        # First operation
        key = idempotency_manager.generate_key(
            user_id="user_001",
            operation_type="checkout",
            data=request_data
        )
        
        idempotency_manager.register_operation(
            key=key,
            order_id=order_id,
            operation_type="checkout",
            request_data=request_data
        )
        
        # Try duplicate
        duplicate = idempotency_manager.check_duplicate(key, request_data)
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.order_id, order_id)
    
    def test_payment_duplicate_validation(self):
        """Test payment-specific duplicate validation"""
        user_id = "user_002"
        order_id = f"ORD_{uuid.uuid4().hex[:8]}"
        
        # First payment
        result1 = payment_validator.validate_payment_request(
            user_id=user_id,
            order_id=order_id,
            amount=2499.00,
            payment_method="CREDIT_CARD"
        )
        
        self.assertEqual(result1["status"], "VALID")
        self.assertTrue(result1["allowed"])
        
        # Mark as completed
        idempotency_manager.mark_completed(
            result1["idempotency_key"],
            {"payment_id": "PAY_001"}
        )
        
        # Try duplicate
        result2 = payment_validator.validate_payment_request(
            user_id=user_id,
            order_id=order_id,
            amount=2499.00,
            payment_method="CREDIT_CARD"
        )
        
        self.assertEqual(result2["status"], "DUPLICATE")
        self.assertFalse(result2["allowed"])


class TestFailureManagement(unittest.TestCase):
    """Test failure handling for all scenarios"""
    
    def test_out_of_stock_handling(self):
        """Test out-of-stock failure handling"""
        resolution = InventoryFailureHandler.handle_out_of_stock(
            order_id="ORD_123",
            product_id="SHOE_001",
            quantity_requested=2,
            quantity_available=1,
            store_id="STORE_001"
        )
        
        self.assertEqual(resolution.failure_type, FailureType.OUT_OF_STOCK)
        self.assertEqual(resolution.severity, "HIGH")
        self.assertIn("alternate_store", resolution.user_options)
    
    def test_inventory_mismatch_compensation(self):
        """Test inventory mismatch compensation calculation"""
        resolution = InventoryFailureHandler.handle_inventory_mismatch_after_payment(
            order_id="ORD_123",
            product_id="SHOE_001",
            amount_paid=5999.00,
            product_price=5999.00
        )
        
        self.assertEqual(resolution.failure_type, FailureType.INVENTORY_MISMATCH)
        self.assertEqual(resolution.severity, "CRITICAL")
        
        # Check compensation
        comp = resolution.compensation
        self.assertEqual(comp["refund_amount"], 5999.00)
        self.assertEqual(comp["compensation_amount"], 5999.00 * 0.20)
        self.assertEqual(comp["loyalty_points"], int(5999.00 * 10))
    
    def test_payment_failure_handling(self):
        """Test payment failure handling"""
        resolution = PaymentFailureHandler.handle_payment_failed(
            order_id="ORD_123",
            payment_method="CREDIT_CARD",
            amount=2499.00,
            error_code="INSUFFICIENT_FUNDS",
            error_message="Insufficient balance"
        )
        
        self.assertEqual(resolution.failure_type, FailureType.PAYMENT_FAILED)
        self.assertIn("Retry payment", resolution.user_options)
    
    def test_duplicate_payment_handling(self):
        """Test duplicate payment auto-refund"""
        resolution = PaymentFailureHandler.handle_duplicate_payment(
            order_id="ORD_123",
            original_payment_id="PAY_001",
            duplicate_payment_id="PAY_002",
            amount=2499.00
        )
        
        self.assertEqual(resolution.failure_type, FailureType.DUPLICATE_PAYMENT)
        self.assertEqual(resolution.severity, "CRITICAL")
        self.assertIn("AUTO_REFUND", [action for action in resolution.system_actions])


class TestPaymentSafety(unittest.TestCase):
    """Test payment validation and safety"""
    
    def test_payment_amount_validation(self):
        """Test payment amount matching"""
        result = PaymentValidator.validate_payment_amount(
            order_amount=2499.00,
            payment_amount=2499.00
        )
        
        self.assertTrue(result["valid"])
        
        # Test mismatch
        result = PaymentValidator.validate_payment_amount(
            order_amount=2499.00,
            payment_amount=2500.00
        )
        
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"], "AMOUNT_MISMATCH")
    
    def test_payment_lifecycle(self):
        """Test complete payment lifecycle"""
        transaction_id = f"TXN_{uuid.uuid4().hex[:8]}"
        order_id = f"ORD_{uuid.uuid4().hex[:8]}"
        
        # Initiate payment
        result = payment_safety_manager.initiate_payment(
            transaction_id=transaction_id,
            order_id=order_id,
            user_id="user_001",
            amount=2499.00,
            payment_method="CREDIT_CARD",
            idempotency_key=f"KEY_{uuid.uuid4().hex[:8]}"
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], PaymentStatus.INITIATED.value)
    
    def test_refund_lifecycle(self):
        """Test refund state transitions"""
        refund_id = f"REF_{uuid.uuid4().hex[:8]}"
        
        # Initiate refund
        result = refund_manager.initiate_refund(
            refund_id=refund_id,
            order_id="ORD_123",
            transaction_id="TXN_001",
            amount=2499.00,
            reason="ORDER_CANCELLED"
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "INITIATED")
        
        # Update to processing
        refund_manager.update_refund_status(
            refund_id=refund_id,
            status="PROCESSING"
        )
        
        # Complete refund
        refund_manager.update_refund_status(
            refund_id=refund_id,
            status="COMPLETED",
            gateway_reference="REF_GW_001"
        )
        
        # Verify timeline
        refund = refund_manager.get_refund_status(refund_id)
        self.assertEqual(refund["status"], "COMPLETED")
        self.assertEqual(len(refund["timeline"]), 3)


class TestPostPurchaseAgent(unittest.TestCase):
    """Test post-purchase operations"""
    
    def test_return_eligibility(self):
        """Test return eligibility checking"""
        from post_purchase_agent import ReturnManager
        
        return_manager = ReturnManager()
        
        # Eligible return
        result = return_manager.check_return_eligibility(
            order_id="ORD_123",
            order_date=datetime.utcnow().isoformat(),
            order_state=OrderState.DELIVERED,
            product_category="SHOES"
        )
        
        self.assertTrue(result["eligible"])
        
        # Not eligible - non-returnable category
        result = return_manager.check_return_eligibility(
            order_id="ORD_123",
            order_date=datetime.utcnow().isoformat(),
            order_state=OrderState.DELIVERED,
            product_category="UNDERWEAR"
        )
        
        self.assertFalse(result["eligible"])
    
    def test_return_initiation(self):
        """Test return request initiation"""
        result = post_purchase_agent.handle_query(
            query_type="initiate_return",
            query_data={
                "return_id": f"RET_{uuid.uuid4().hex[:8]}",
                "order_id": "ORD_123",
                "user_id": "user_001",
                "product_ids": ["SHOE_001"],
                "reason": ReturnReason.SIZE_FIT_ISSUE,
                "reason_details": "Size too small",
                "refund_amount": 2499.00
            }
        )
        
        self.assertTrue(result["success"])
        self.assertIn("return_id", result)
        self.assertIn("pickup_date", result)
    
    def test_exchange_initiation(self):
        """Test exchange request initiation"""
        result = post_purchase_agent.handle_query(
            query_type="initiate_exchange",
            query_data={
                "exchange_id": f"EXC_{uuid.uuid4().hex[:8]}",
                "order_id": "ORD_123",
                "user_id": "user_001",
                "original_product_id": "SHOE_001_SIZE_9",
                "requested_product_id": "SHOE_001_SIZE_10",
                "exchange_type": ExchangeType.SIZE_EXCHANGE,
                "reason": "Size too small",
                "original_price": 2499.00,
                "new_price": 2499.00
            }
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["price_difference"], 0.0)


class TestTransactionTrust(unittest.TestCase):
    """Test transaction trust mechanisms"""
    
    def test_retry_policy(self):
        """Test retry policy calculations"""
        policy = RetryPolicy(max_attempts=3, base_delay=1.0)
        
        # Should retry on attempt 1
        self.assertTrue(policy.should_retry(1, Exception("Temporary error")))
        
        # Should not retry after max attempts
        self.assertFalse(policy.should_retry(3, Exception("Temporary error")))
        
        # Check delay calculation
        delay1 = policy.calculate_delay(1)
        delay2 = policy.calculate_delay(2)
        self.assertLess(delay1, delay2)  # Exponential backoff
    
    def test_transaction_rollback(self):
        """Test distributed transaction rollback"""
        tx_id = f"TX_{uuid.uuid4().hex[:8]}"
        
        # Begin transaction
        tx = transaction_manager.begin_transaction(
            transaction_id=tx_id,
            transaction_type="checkout"
        )
        
        self.assertEqual(tx.transaction_id, tx_id)
        
        # Add steps
        transaction_manager.add_step(
            transaction_id=tx_id,
            step_name="reserve_inventory"
        )
        
        transaction_manager.add_step(
            transaction_id=tx_id,
            step_name="process_payment"
        )
        
        # Rollback
        result = transaction_manager.rollback(
            transaction_id=tx_id,
            reason="Payment failed"
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["rollback_results"]), 2)
    
    def test_audit_logging(self):
        """Test audit log creation and querying"""
        # Create audit log
        log_id = audit_logger.log(
            service="TestService",
            action="TEST_ACTION",
            resource_type="ORDER",
            resource_id="ORD_TEST",
            status="SUCCESS",
            details={"test": "data"},
            user_id="user_001"
        )
        
        self.assertIsNotNone(log_id)
        
        # Query logs
        logs = audit_logger.query_logs(
            filters={"user_id": "user_001"},
            limit=10
        )
        
        self.assertGreater(len(logs), 0)
        self.assertEqual(logs[-1]["resource_id"], "ORD_TEST")


class TestIntegration(unittest.TestCase):
    """Integration tests for complete flows"""
    
    def test_complete_checkout_flow(self):
        """Test complete checkout with all safety checks"""
        user_id = "user_integration"
        order_id = f"ORD_{uuid.uuid4().hex[:8]}"
        transaction_id = f"TXN_{uuid.uuid4().hex[:8]}"
        amount = 2499.00
        
        # Step 1: Validate payment (idempotency)
        validation = payment_validator.validate_payment_request(
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            payment_method="CREDIT_CARD"
        )
        
        self.assertTrue(validation["allowed"])
        
        # Step 2: Begin transaction
        tx = transaction_manager.begin_transaction(
            transaction_id=f"TX_{uuid.uuid4().hex[:8]}",
            transaction_type="checkout"
        )
        
        # Step 3: Process payment
        payment_result = payment_safety_manager.initiate_payment(
            transaction_id=transaction_id,
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            payment_method="CREDIT_CARD",
            idempotency_key=validation["idempotency_key"]
        )
        
        self.assertTrue(payment_result["success"])
        
        # Step 4: Commit transaction
        transaction_manager.commit(tx.transaction_id)
        
        # Step 5: Audit log
        audit_logger.log(
            service="IntegrationTest",
            action="CHECKOUT_COMPLETED",
            resource_type="ORDER",
            resource_id=order_id,
            status="SUCCESS",
            details={"amount": amount},
            user_id=user_id
        )


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    print("=" * 80)
    print("MEMBER 4 - PRODUCTION SAFETY TEST SUITE")
    print("=" * 80)
    print()
    
    run_tests()
