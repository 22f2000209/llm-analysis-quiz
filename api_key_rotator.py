"""
API Key Rotation Manager for avoiding rate limits.
Cycles through multiple Google API keys.
"""

import os
from typing import List
import threading

class APIKeyRotator:
    """Manages rotation of multiple API keys to avoid rate limits."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._current_index = 0
        self._api_keys = self._load_api_keys()
        self._exhausted_keys = set()  # Track rate-limited keys
        self._all_exhausted = False    # Flag when all keys are exhausted
        
        if not self._api_keys:
            raise ValueError("No Google API keys found in environment")
        
        print(f"[API_ROTATOR] Loaded {len(self._api_keys)} API key(s)")
    
    def _load_api_keys(self) -> List[str]:
        """Load all Google API keys from environment."""
        keys = []
        
        # Primary key
        primary_key = os.getenv("GOOGLE_API_KEY")
        if primary_key:
            keys.append(primary_key)
        
        # Additional keys: GOOGLE_API_KEY_2, GOOGLE_API_KEY_3, etc.
        i = 2
        while True:
            key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if not key:
                break
            keys.append(key)
            i += 1
        
        return keys
    
    def get_next_key(self) -> str:
        """Get the next API key in rotation."""
        with self._lock:
            key = self._api_keys[self._current_index]
            self._current_index = (self._current_index + 1) % len(self._api_keys)
            
            # Log which key we're using (show only last 4 chars for security)
            key_preview = f"...{key[-4:]}" if len(key) > 4 else "****"
            print(f"[API_ROTATOR] Using key {self._current_index}/{len(self._api_keys)}: {key_preview}")
            
            return key
    
    def get_current_key(self) -> str:
        """Get the current API key without rotating."""
        with self._lock:
            return self._api_keys[self._current_index]
    
    def mark_key_exhausted(self, key_index: int):
        """Mark a specific key as rate-limited/exhausted."""
        with self._lock:
            self._exhausted_keys.add(key_index)
            print(f"[API_ROTATOR] ⚠️ Key {key_index + 1}/{len(self._api_keys)} marked as exhausted")
            
            # Check if all keys are now exhausted
            if len(self._exhausted_keys) >= len(self._api_keys):
                self._all_exhausted = True
                print(f"[API_ROTATOR] 🚨 ALL {len(self._api_keys)} Gemini keys exhausted! Switching to OpenAI.")
    
    def are_all_keys_exhausted(self) -> bool:
        """Check if all API keys have been exhausted."""
        with self._lock:
            return self._all_exhausted
    
    def reset_exhaustion(self):
        """Reset exhaustion tracking (useful for new sessions or after cooldown)."""
        with self._lock:
            self._exhausted_keys.clear()
            self._all_exhausted = False
            print(f"[API_ROTATOR] ✓ Exhaustion tracking reset")
    
    @property
    def key_count(self) -> int:
        """Number of available API keys."""
        return len(self._api_keys)


# Global instance
_rotator = None

def get_api_key_rotator() -> APIKeyRotator:
    """Get or create the global API key rotator."""
    global _rotator
    if _rotator is None:
        _rotator = APIKeyRotator()
    return _rotator

def get_next_google_api_key() -> str:
    """Get the next Google API key in rotation."""
    return get_api_key_rotator().get_next_key()
