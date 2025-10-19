"""
In-memory buffer for storing enriched telemetry data received via webhooks.
"""
from collections import deque
from typing import List, Optional
import logging
from models.input_models import EnrichedTelemetryWebhook

logger = logging.getLogger(__name__)


class TelemetryBuffer:
    """In-memory buffer for enriched telemetry data."""
    
    def __init__(self, max_size: int = 100):
        """
        Initialize telemetry buffer.
        
        Args:
            max_size: Maximum number of records to store
        """
        self._buffer = deque(maxlen=max_size)
        self.max_size = max_size
        logger.info(f"Telemetry buffer initialized (max_size={max_size})")
    
    def add(self, telemetry: EnrichedTelemetryWebhook):
        """
        Add telemetry record to buffer.
        
        Args:
            telemetry: Enriched telemetry data
        """
        self._buffer.append(telemetry)
        logger.debug(f"Added telemetry for lap {telemetry.lap} (buffer size: {len(self._buffer)})")
    
    def get_latest(self, limit: int = 10) -> List[EnrichedTelemetryWebhook]:
        """
        Get latest telemetry records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of most recent telemetry records (newest first)
        """
        # Get last N items, return in reverse order (newest first)
        items = list(self._buffer)[-limit:]
        items.reverse()
        return items
    
    def get_all(self) -> List[EnrichedTelemetryWebhook]:
        """
        Get all telemetry records in buffer.
        
        Returns:
            List of all telemetry records (newest first)
        """
        items = list(self._buffer)
        items.reverse()
        return items
    
    def size(self) -> int:
        """
        Get current buffer size.
        
        Returns:
            Number of records in buffer
        """
        return len(self._buffer)
    
    def clear(self):
        """Clear all records from buffer."""
        self._buffer.clear()
        logger.info("Telemetry buffer cleared")
