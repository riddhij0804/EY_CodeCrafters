# Inventory Agent Client
# HTTP client for connecting to the Inventory Agent microservice

import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8001")
INVENTORY_TIMEOUT = int(os.getenv("INVENTORY_TIMEOUT", "5"))


class InventoryClient:
    """Client for communicating with the Inventory Agent microservice."""
    
    def __init__(self, base_url: str = None, timeout: int = None):
        """
        Initialize the inventory client.
        
        Args:
            base_url: Inventory service URL (defaults to env var or localhost:8001)
            timeout: Request timeout in seconds (default: 5)
        """
        self.base_url = (base_url or INVENTORY_SERVICE_URL).rstrip('/')
        self.timeout = timeout or INVENTORY_TIMEOUT
        self._health_checked = False
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to inventory service.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json: Request body (for POST/PUT)
            headers: Additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.exceptions.RequestException: On network/HTTP errors
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=json,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise Exception(f"Inventory service timeout after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to inventory service at {self.base_url}")
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get('detail', str(e)) if e.response.content else str(e)
            raise Exception(f"Inventory service error: {error_detail}")
    
    def health_check(self) -> bool:
        """
        Check if inventory service is healthy.
        
        Returns:
            True if service is available and Redis connected
        """
        try:
            response = self._make_request("GET", "/health")
            self._health_checked = response.get("status") == "healthy"
            return self._health_checked
        except Exception as e:
            print(f"⚠️ Inventory service health check failed: {e}")
            return False
    
    def get_inventory(self, sku: str) -> Dict[str, Any]:
        """
        Get stock levels for a SKU across all locations.
        
        Args:
            sku: Product SKU
            
        Returns:
            {
                "sku": "SKU000001",
                "online_stock": 500,
                "store_stock": {"STORE_MUMBAI": 182, ...},
                "total_stock": 1293
            }
        """
        return self._make_request("GET", f"/inventory/{sku}")
    
    def create_hold(
        self,
        sku: str,
        quantity: int,
        location: str = "online",
        ttl: int = 300,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an inventory hold (atomic stock decrement).
        
        Args:
            sku: Product SKU
            quantity: Quantity to hold
            location: "online" or "store:{store_id}"
            ttl: Hold duration in seconds (default: 300 = 5 minutes)
            idempotency_key: Optional key for duplicate prevention
            
        Returns:
            {
                "hold_id": "hold-xxx",
                "sku": "SKU000001",
                "quantity": 3,
                "location": "online",
                "remaining_stock": 497,
                "expires_at": "2025-12-07T18:44:44",
                "status": "active"
            }
        """
        headers = {}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        
        return self._make_request(
            "POST",
            "/hold",
            json={
                "sku": sku,
                "quantity": quantity,
                "location": location,
                "ttl": ttl
            },
            headers=headers
        )
    
    def release_hold(self, hold_id: str) -> Dict[str, Any]:
        """
        Release an inventory hold (restore stock).
        
        Args:
            hold_id: Hold ID from create_hold()
            
        Returns:
            {
                "hold_id": "hold-xxx",
                "status": "released",
                "restored_stock": 500
            }
        """
        return self._make_request(
            "POST",
            "/release",
            json={"hold_id": hold_id}
        )
    
    def simulate_sale(
        self,
        sku: str,
        quantity: int,
        location: str = "online"
    ) -> Dict[str, Any]:
        """
        Simulate a sale by decrementing stock.
        For demo/testing purposes. Bypasses hold mechanism.
        
        Args:
            sku: Product SKU
            quantity: Quantity sold
            location: "online" or "store:{store_id}"
            
        Returns:
            {
                "sku": "SKU000001",
                "quantity_sold": 2,
                "location": "online",
                "remaining_stock": 498,
                "status": "sold"
            }
        """
        return self._make_request(
            "POST",
            "/simulate/sale",
            json={
                "sku": sku,
                "quantity": quantity,
                "location": location
            }
        )
    
    def check_availability(self, sku: str, quantity: int, location: str = "online") -> bool:
        """
        Check if sufficient stock is available (convenience method).
        
        Args:
            sku: Product SKU
            quantity: Desired quantity
            location: "online" or "store:{store_id}"
            
        Returns:
            True if stock available, False otherwise
        """
        try:
            inventory = self.get_inventory(sku)
            
            if location == "online":
                return inventory["online_stock"] >= quantity
            elif location.startswith("store:"):
                store_id = location.split(":", 1)[1]
                return inventory["store_stock"].get(store_id, 0) >= quantity
            else:
                return False
                
        except Exception:
            return False


# ==========================================
# INTEGRATION HELPERS
# ==========================================

def get_inventory_client() -> InventoryClient:
    """
    Get singleton inventory client instance.
    
    Usage:
        client = get_inventory_client()
        stock = client.get_inventory("SKU000001")
    """
    if not hasattr(get_inventory_client, "_client"):
        get_inventory_client._client = InventoryClient()
    return get_inventory_client._client


def check_stock_availability(sku: str, quantity: int = 1, location: str = "online") -> Dict[str, Any]:
    """
    Check stock availability (backward compatible with existing code).
    
    This function can be used as a drop-in replacement for the mock
    check_stock_levels() function in the notebook.
    
    Args:
        sku: Product SKU
        quantity: Desired quantity (default: 1)
        location: "online" or "store:{store_id}" (default: "online")
    
    Returns:
        {
            "available": True/False,
            "current_stock": 500,
            "requested": 1,
            "location": "online"
        }
    """
    try:
        client = get_inventory_client()
        inventory = client.get_inventory(sku)
        
        if location == "online":
            current = inventory["online_stock"]
        elif location.startswith("store:"):
            store_id = location.split(":", 1)[1]
            current = inventory["store_stock"].get(store_id, 0)
        else:
            current = 0
        
        return {
            "available": current >= quantity,
            "current_stock": current,
            "requested": quantity,
            "location": location,
            "sku": sku
        }
        
    except Exception as e:
        print(f"⚠️ Inventory check failed: {e}")
        # Return pessimistic result on error
        return {
            "available": False,
            "current_stock": 0,
            "requested": quantity,
            "location": location,
            "sku": sku,
            "error": str(e)
        }


# ==========================================
# EXAMPLE USAGE
# ==========================================

if __name__ == "__main__":
    """
    Test the inventory client.
    
    Run this script to verify connectivity:
        python inventory_client.py
    """
    print("🧪 Testing Inventory Client")
    print("=" * 60)
    
    client = InventoryClient()
    
    # 1. Health check
    print("\n1. Health Check:")
    healthy = client.health_check()
    print(f"   {'✅' if healthy else '❌'} Service healthy: {healthy}")
    
    if not healthy:
        print("\n⚠️ Inventory service not available. Start it with:")
        print("   cd backend/agents/worker_agents/inventory")
        print("   python app.py")
        exit(1)
    
    # 2. Get inventory
    print("\n2. Get Inventory:")
    try:
        stock = client.get_inventory("SKU000001")
        print(f"   ✅ SKU000001 online stock: {stock['online_stock']}")
        print(f"   ✅ Total stock: {stock['total_stock']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Create hold
    print("\n3. Create Hold:")
    try:
        hold = client.create_hold("SKU000001", 2, location="online", ttl=60)
        print(f"   ✅ Hold created: {hold['hold_id']}")
        print(f"   ✅ Remaining stock: {hold['remaining_stock']}")
        
        # 4. Release hold
        print("\n4. Release Hold:")
        release = client.release_hold(hold['hold_id'])
        print(f"   ✅ Hold released: {release['status']}")
        print(f"   ✅ Restored stock: {release['restored_stock']}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 5. Check availability
    print("\n5. Check Availability:")
    available = client.check_availability("SKU000001", 10, "online")
    print(f"   {'✅' if available else '❌'} 10 units available: {available}")
    
    print("\n" + "=" * 60)
    print("✅ Inventory client tests complete!")
