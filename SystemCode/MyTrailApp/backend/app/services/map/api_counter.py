"""
API Call Counter - Simple call limiting implementation
"""
from datetime import datetime, date
from typing import Dict
from app.config import settings

class APICounter:
    """API call counter"""
    
    def __init__(self):
        self.call_count: Dict[str, int] = {}
        self.current_date = date.today()
    
    def can_make_call(self) -> bool:
        """Check if API can be called"""
        today = date.today()
        
        # Reset counter if date changes
        if today != self.current_date:
            self.call_count.clear()
            self.current_date = today
        
        # Get today's call count
        today_key = today.isoformat()
        current_calls = self.call_count.get(today_key, 0)
        
        return current_calls < settings.max_api_calls_per_day
    
    def record_call(self) -> None:
        """Record one API call"""
        today = date.today()
        today_key = today.isoformat()
        
        if today_key not in self.call_count:
            self.call_count[today_key] = 0
        
        self.call_count[today_key] += 1
    
    def get_remaining_calls(self) -> int:
        """Get remaining call count"""
        today = date.today()
        today_key = today.isoformat()
        current_calls = self.call_count.get(today_key, 0)
        
        return max(0, settings.max_api_calls_per_day - current_calls)

# Global counter instance
api_counter = APICounter()
