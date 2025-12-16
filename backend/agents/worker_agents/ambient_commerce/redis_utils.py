# Redis utilities for caching search results and feature vectors
# Optimizes performance by caching extracted features and search results

import redis
import json
import pickle
import numpy as np
from typing import Optional, Dict, Any
import hashlib


class RedisCache:
    """
    Redis cache manager for the Ambient Commerce agent.
    Caches feature vectors and search results.
    """
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 7):
        """
        Initialize Redis connection.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number (use 7 to avoid conflicts with other agents)
        """
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=False  # We'll handle encoding/decoding
            )
            self.redis_client.ping()
            self.connected = True
            print(f"Redis connected: {host}:{port} (db={db})")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None
            self.connected = False
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """
        Generate a cache key.
        
        Args:
            prefix: Key prefix (e.g., 'features', 'search')
            identifier: Unique identifier (e.g., image path hash)
            
        Returns:
            Cache key string
        """
        return f"ambient_commerce:{prefix}:{identifier}"
    
    def _hash_image_path(self, image_path: str) -> str:
        """
        Generate a hash for an image path.
        
        Args:
            image_path: Path to the image
            
        Returns:
            MD5 hash of the path
        """
        return hashlib.md5(image_path.encode()).hexdigest()
    
    def cache_features(self, image_path: str, features: np.ndarray, ttl: int = 3600) -> bool:
        """
        Cache extracted features for an image.
        
        Args:
            image_path: Path to the image
            features: Feature vector (numpy array)
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if cached successfully
        """
        if not self.connected:
            return False
        
        try:
            key = self._generate_key("features", self._hash_image_path(image_path))
            
            # Serialize numpy array
            features_bytes = pickle.dumps(features)
            
            # Store in Redis with TTL
            self.redis_client.setex(key, ttl, features_bytes)
            return True
        except Exception as e:
            print(f"Failed to cache features: {e}")
            return False
    
    def get_cached_features(self, image_path: str) -> Optional[np.ndarray]:
        """
        Get cached features for an image.
        
        Args:
            image_path: Path to the image
            
        Returns:
            Cached feature vector or None if not found
        """
        if not self.connected:
            return None
        
        try:
            key = self._generate_key("features", self._hash_image_path(image_path))
            features_bytes = self.redis_client.get(key)
            
            if features_bytes:
                return pickle.loads(features_bytes)
            return None
        except Exception as e:
            print(f"Failed to get cached features: {e}")
            return None
    
    def cache_search_result(self, query_hash: str, result: Dict, ttl: int = 1800) -> bool:
        """
        Cache search result.
        
        Args:
            query_hash: Hash of the query parameters
            result: Search result dictionary
            ttl: Time to live in seconds (default: 30 minutes)
            
        Returns:
            True if cached successfully
        """
        if not self.connected:
            return False
        
        try:
            key = self._generate_key("search", query_hash)
            
            # Serialize result
            result_json = json.dumps(result, default=str)
            
            # Store in Redis with TTL
            self.redis_client.setex(key, ttl, result_json)
            return True
        except Exception as e:
            print(f"Failed to cache search result: {e}")
            return False
    
    def get_cached_search_result(self, query_hash: str) -> Optional[Dict]:
        """
        Get cached search result.
        
        Args:
            query_hash: Hash of the query parameters
            
        Returns:
            Cached search result or None if not found
        """
        if not self.connected:
            return None
        
        try:
            key = self._generate_key("search", query_hash)
            result_json = self.redis_client.get(key)
            
            if result_json:
                return json.loads(result_json)
            return None
        except Exception as e:
            print(f"Failed to get cached search result: {e}")
            return None
    
    def generate_query_hash(self, image_path: str, **params) -> str:
        """
        Generate a hash for a search query.
        
        Args:
            image_path: Path to query image
            **params: Additional query parameters
            
        Returns:
            Query hash
        """
        query_str = f"{image_path}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def increment_search_count(self, sku: str) -> int:
        """
        Increment search count for a product.
        
        Args:
            sku: Product SKU
            
        Returns:
            New count
        """
        if not self.connected:
            return 0
        
        try:
            key = self._generate_key("count", sku)
            return self.redis_client.incr(key)
        except Exception as e:
            print(f"Failed to increment search count: {e}")
            return 0
    
    def get_search_count(self, sku: str) -> int:
        """
        Get search count for a product.
        
        Args:
            sku: Product SKU
            
        Returns:
            Search count
        """
        if not self.connected:
            return 0
        
        try:
            key = self._generate_key("count", sku)
            count = self.redis_client.get(key)
            return int(count) if count else 0
        except Exception as e:
            print(f"Failed to get search count: {e}")
            return 0
    
    def clear_cache(self, pattern: str = "ambient_commerce:*") -> int:
        """
        Clear cache entries matching a pattern.
        
        Args:
            pattern: Redis key pattern (default: all ambient_commerce keys)
            
        Returns:
            Number of keys deleted
        """
        if not self.connected:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Failed to clear cache: {e}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Redis health and return statistics.
        
        Returns:
            Dictionary with health information
        """
        if not self.connected:
            return {
                "connected": False,
                "message": "Redis not connected"
            }
        
        try:
            info = self.redis_client.info()
            num_keys = len(self.redis_client.keys("ambient_commerce:*"))
            
            return {
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "ambient_commerce_keys": num_keys,
                "message": "Redis healthy"
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "message": "Redis health check failed"
            }


# Global cache instance
_cache_instance = None


def get_cache() -> RedisCache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


def clear_cache():
    """Clear all ambient commerce cache."""
    cache = get_cache()
    return cache.clear_cache()


if __name__ == "__main__":
    # Test Redis connection
    cache = RedisCache()
    health = cache.health_check()
    print("Redis Health Check:")
    print(json.dumps(health, indent=2))
