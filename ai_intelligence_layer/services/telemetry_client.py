"""
Telemetry client for fetching enriched data from HPC enrichment service.
"""
import httpx
import logging
from typing import List, Optional
from config import get_settings
from models.input_models import EnrichedTelemetryWebhook

logger = logging.getLogger(__name__)


class TelemetryClient:
    """Client for fetching enriched telemetry from enrichment service."""
    
    def __init__(self):
        """Initialize telemetry client."""
        settings = get_settings()
        self.base_url = settings.enrichment_service_url
        self.fetch_limit = settings.enrichment_fetch_limit
        logger.info(f"Telemetry client initialized for {self.base_url}")
    
    async def fetch_latest(self, limit: Optional[int] = None) -> List[EnrichedTelemetryWebhook]:
        """
        Fetch latest enriched telemetry records from enrichment service.
        
        Args:
            limit: Number of records to fetch (defaults to config setting)
            
        Returns:
            List of enriched telemetry records
            
        Raises:
            Exception: If request fails
        """
        if limit is None:
            limit = self.fetch_limit
        
        url = f"{self.base_url}/enriched"
        params = {"limit": limit}
        
        try:
            logger.info(f"Fetching telemetry from {url} (limit={limit})")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Fetched {len(data)} telemetry records")
                
                # Parse into Pydantic models
                records = [EnrichedTelemetryWebhook(**item) for item in data]
                return records
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching telemetry: {e.response.status_code}")
            raise Exception(f"Enrichment service returned error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error fetching telemetry: {e}")
            raise Exception(f"Cannot connect to enrichment service at {self.base_url}")
        except Exception as e:
            logger.error(f"Unexpected error fetching telemetry: {e}")
            raise
    
    async def health_check(self) -> bool:
        """
        Check if enrichment service is reachable.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
