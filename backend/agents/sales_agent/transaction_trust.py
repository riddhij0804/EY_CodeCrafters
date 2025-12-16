"""
Transaction Trust Layer - System-Level Realism
Member 4 Responsibility: Rollbacks, Timeouts, Retries, Audit Logs

Makes the system production-ready and non-academic
"""
import logging
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class TransactionStatus(str, Enum):
    """Transaction lifecycle status"""
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


@dataclass
class Transaction:
    """
    Represents a distributed transaction
    """
    transaction_id: str
    transaction_type: str
    status: TransactionStatus
    started_at: str
    completed_at: Optional[str]
    steps: list
    rollback_steps: list
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "steps": self.steps,
            "metadata": self.metadata
        }


@dataclass
class AuditLogEntry:
    """
    Audit log entry for compliance and debugging
    """
    log_id: str
    timestamp: str
    service: str
    action: str
    resource_type: str
    resource_id: str
    user_id: Optional[str]
    status: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp,
            "service": self.service,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "status": self.status,
            "details": self.details,
            "ip_address": self.ip_address
        }


class RetryPolicy:
    """
    Retry policy for transient failures
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry using exponential backoff
        
        Args:
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = min(
            self.base_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )
        
        # Add jitter (±20%) to prevent thundering herd
        import random
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        
        return max(0, delay + jitter)
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """
        Determine if operation should be retried
        
        Args:
            attempt: Current attempt number
            error: Error that occurred
            
        Returns:
            True if should retry
        """
        if attempt >= self.max_attempts:
            logger.info(f"Max retry attempts ({self.max_attempts}) reached")
            return False
        
        # Check if error is retryable
        retryable_errors = [
            "TimeoutError",
            "ConnectionError",
            "TemporaryFailure",
            "ServiceUnavailable"
        ]
        
        error_type = type(error).__name__
        is_retryable = any(err in error_type for err in retryable_errors)
        
        if not is_retryable:
            logger.info(f"Error type {error_type} is not retryable")
            return False
        
        return True


class RetryExecutor:
    """
    Executes operations with retry logic
    """
    
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()
    
    def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute operation with automatic retry
        
        Args:
            operation: Function to execute
            operation_name: Name for logging
            *args, **kwargs: Arguments to pass to operation
            
        Returns:
            Operation result or error information
        """
        attempt = 0
        last_error = None
        
        while attempt < self.policy.max_attempts:
            attempt += 1
            
            try:
                logger.info(
                    f"Executing {operation_name} (attempt {attempt}/{self.policy.max_attempts})"
                )
                
                result = operation(*args, **kwargs)
                
                logger.info(f"{operation_name} succeeded on attempt {attempt}")
                
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt
                }
            
            except Exception as e:
                last_error = e
                logger.warning(
                    f"{operation_name} failed on attempt {attempt}: {str(e)}"
                )
                
                if not self.policy.should_retry(attempt, e):
                    break
                
                if attempt < self.policy.max_attempts:
                    delay = self.policy.calculate_delay(attempt)
                    logger.info(f"Retrying after {delay:.2f} seconds...")
                    time.sleep(delay)
        
        logger.error(
            f"{operation_name} failed after {attempt} attempts: {str(last_error)}"
        )
        
        return {
            "success": False,
            "error": str(last_error),
            "error_type": type(last_error).__name__,
            "attempts": attempt
        }


class TimeoutManager:
    """
    Manages operation timeouts
    """
    
    DEFAULT_TIMEOUTS = {
        "payment_processing": 30,  # seconds
        "inventory_check": 5,
        "order_creation": 10,
        "refund_processing": 30,
        "api_call": 15
    }
    
    @classmethod
    def get_timeout(cls, operation_type: str) -> int:
        """
        Get timeout for operation type
        
        Args:
            operation_type: Type of operation
            
        Returns:
            Timeout in seconds
        """
        return cls.DEFAULT_TIMEOUTS.get(operation_type, 10)
    
    @staticmethod
    def execute_with_timeout(
        operation: Callable,
        timeout: int,
        operation_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute operation with timeout
        
        Args:
            operation: Function to execute
            timeout: Timeout in seconds
            operation_name: Name for logging
            *args, **kwargs: Arguments to pass to operation
            
        Returns:
            Operation result or timeout error
        """
        import threading
        
        result = {"success": False, "error": "Operation not completed"}
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                result = {
                    "success": True,
                    "result": operation(*args, **kwargs)
                }
            except Exception as e:
                exception = e
                result = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            logger.error(
                f"{operation_name} timed out after {timeout} seconds"
            )
            return {
                "success": False,
                "error": "TIMEOUT",
                "message": f"Operation timed out after {timeout} seconds",
                "timeout": timeout
            }
        
        if exception:
            logger.error(f"{operation_name} failed: {exception}")
        
        return result


class TransactionManager:
    """
    Manages distributed transactions with rollback capability
    """
    
    def __init__(self):
        self.transactions: Dict[str, Transaction] = {}
    
    def begin_transaction(
        self,
        transaction_id: str,
        transaction_type: str,
        metadata: Optional[Dict] = None
    ) -> Transaction:
        """
        Begin a new transaction
        
        Args:
            transaction_id: Unique transaction identifier
            transaction_type: Type of transaction (checkout, refund, etc.)
            metadata: Additional transaction metadata
            
        Returns:
            Created transaction
        """
        transaction = Transaction(
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            status=TransactionStatus.STARTED,
            started_at=datetime.utcnow().isoformat(),
            completed_at=None,
            steps=[],
            rollback_steps=[],
            metadata=metadata or {}
        )
        
        self.transactions[transaction_id] = transaction
        
        logger.info(
            f"Transaction started: {transaction_id} ({transaction_type})"
        )
        
        return transaction
    
    def add_step(
        self,
        transaction_id: str,
        step_name: str,
        rollback_action: Optional[Callable] = None,
        rollback_data: Optional[Dict] = None
    ) -> bool:
        """
        Add a step to transaction with rollback action
        
        Args:
            transaction_id: Transaction identifier
            step_name: Name of the step
            rollback_action: Function to call for rollback
            rollback_data: Data needed for rollback
            
        Returns:
            True if step added successfully
        """
        if transaction_id not in self.transactions:
            logger.error(f"Transaction not found: {transaction_id}")
            return False
        
        transaction = self.transactions[transaction_id]
        
        step = {
            "step_name": step_name,
            "completed_at": datetime.utcnow().isoformat(),
            "status": "COMPLETED"
        }
        
        transaction.steps.append(step)
        
        if rollback_action:
            transaction.rollback_steps.insert(0, {
                "step_name": step_name,
                "rollback_action": rollback_action,
                "rollback_data": rollback_data
            })
        
        logger.info(
            f"Transaction {transaction_id}: Step '{step_name}' completed"
        )
        
        return True
    
    def commit(self, transaction_id: str) -> bool:
        """
        Commit transaction (success path)
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            True if committed successfully
        """
        if transaction_id not in self.transactions:
            logger.error(f"Transaction not found: {transaction_id}")
            return False
        
        transaction = self.transactions[transaction_id]
        transaction.status = TransactionStatus.COMMITTED
        transaction.completed_at = datetime.utcnow().isoformat()
        
        logger.info(f"Transaction committed: {transaction_id}")
        
        return True
    
    def rollback(
        self,
        transaction_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Rollback transaction (undo all steps)
        
        Args:
            transaction_id: Transaction identifier
            reason: Reason for rollback
            
        Returns:
            Rollback result
        """
        if transaction_id not in self.transactions:
            logger.error(f"Transaction not found: {transaction_id}")
            return {
                "success": False,
                "error": "Transaction not found"
            }
        
        transaction = self.transactions[transaction_id]
        
        logger.warning(
            f"Rolling back transaction {transaction_id}: {reason}"
        )
        
        rollback_results = []
        
        # Execute rollback steps in reverse order
        for rollback_step in transaction.rollback_steps:
            step_name = rollback_step["step_name"]
            rollback_action = rollback_step.get("rollback_action")
            rollback_data = rollback_step.get("rollback_data", {})
            
            try:
                if rollback_action:
                    logger.info(f"Executing rollback for step: {step_name}")
                    rollback_action(**rollback_data)
                    
                    rollback_results.append({
                        "step": step_name,
                        "status": "ROLLED_BACK"
                    })
                else:
                    rollback_results.append({
                        "step": step_name,
                        "status": "NO_ROLLBACK_ACTION"
                    })
            
            except Exception as e:
                logger.error(
                    f"Rollback failed for step {step_name}: {str(e)}"
                )
                rollback_results.append({
                    "step": step_name,
                    "status": "ROLLBACK_FAILED",
                    "error": str(e)
                })
        
        transaction.status = TransactionStatus.ROLLED_BACK
        transaction.completed_at = datetime.utcnow().isoformat()
        transaction.metadata["rollback_reason"] = reason
        transaction.metadata["rollback_results"] = rollback_results
        
        logger.info(
            f"Transaction {transaction_id} rolled back. "
            f"Steps reversed: {len(rollback_results)}"
        )
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "rollback_results": rollback_results,
            "message": f"Transaction rolled back: {reason}"
        }


class AuditLogger:
    """
    Comprehensive audit logging for compliance
    """
    
    def __init__(self):
        self.audit_logs: list = []
    
    def log(
        self,
        service: str,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Create audit log entry
        
        Args:
            service: Service that performed action
            action: Action performed
            resource_type: Type of resource affected
            resource_id: Resource identifier
            status: Action status (SUCCESS, FAILURE, etc.)
            details: Detailed information
            user_id: User who performed action
            ip_address: IP address of request
            
        Returns:
            Log entry ID
        """
        import uuid
        
        log_id = f"AUDIT_{uuid.uuid4().hex[:12]}"
        
        entry = AuditLogEntry(
            log_id=log_id,
            timestamp=datetime.utcnow().isoformat(),
            service=service,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            status=status,
            details=details,
            ip_address=ip_address
        )
        
        self.audit_logs.append(entry)
        
        # In production, this would write to:
        # - Secure audit database
        # - SIEM system
        # - Log aggregation service
        logger.info(f"AUDIT: [{action}] {resource_type}/{resource_id} - {status}")
        
        return log_id
    
    def query_logs(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> list:
        """
        Query audit logs with filters
        
        Args:
            filters: Filter criteria
            limit: Maximum number of results
            
        Returns:
            Filtered audit log entries
        """
        results = self.audit_logs
        
        if filters:
            if "user_id" in filters:
                results = [
                    log for log in results
                    if log.user_id == filters["user_id"]
                ]
            
            if "resource_type" in filters:
                results = [
                    log for log in results
                    if log.resource_type == filters["resource_type"]
                ]
            
            if "action" in filters:
                results = [
                    log for log in results
                    if log.action == filters["action"]
                ]
            
            if "status" in filters:
                results = [
                    log for log in results
                    if log.status == filters["status"]
                ]
        
        return [log.to_dict() for log in results[-limit:]]


class CircuitBreaker:
    """
    Circuit breaker pattern for failing fast
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute operation through circuit breaker
        
        Args:
            operation: Function to execute
            *args, **kwargs: Arguments to pass to operation
            
        Returns:
            Operation result or circuit breaker error
        """
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (
                    datetime.utcnow() - 
                    datetime.fromisoformat(self.last_failure_time)
                ).seconds
                
                if elapsed > self.recovery_timeout:
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = "HALF_OPEN"
                else:
                    logger.warning("Circuit breaker is OPEN - failing fast")
                    return {
                        "success": False,
                        "error": "CIRCUIT_BREAKER_OPEN",
                        "message": "Service temporarily unavailable",
                        "retry_after": self.recovery_timeout - elapsed
                    }
        
        try:
            result = operation(*args, **kwargs)
            
            # Success - reset circuit breaker
            if self.state == "HALF_OPEN":
                logger.info("Circuit breaker closing - service recovered")
                self.state = "CLOSED"
                self.failure_count = 0
            
            return {
                "success": True,
                "result": result
            }
        
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow().isoformat()
            
            logger.warning(
                f"Circuit breaker failure {self.failure_count}/{self.failure_threshold}"
            )
            
            if self.failure_count >= self.failure_threshold:
                logger.error("Circuit breaker opening - too many failures")
                self.state = "OPEN"
            
            return {
                "success": False,
                "error": str(e),
                "circuit_breaker_state": self.state
            }


# Global instances
retry_executor = RetryExecutor()
transaction_manager = TransactionManager()
audit_logger = AuditLogger()
