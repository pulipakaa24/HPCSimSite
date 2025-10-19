"""
Gemini API client wrapper with retry logic and error handling.
"""
import google.generativeai as genai
import json
import logging
import time
from typing import Dict, Any, Optional
from config import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper for Google Gemini API with retry logic and JSON parsing."""
    
    def __init__(self):
        """Initialize Gemini client with API key from settings."""
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.max_retries = settings.gemini_max_retries
        self.demo_mode = settings.demo_mode
        
        # Cache for demo mode
        self._demo_cache: Dict[str, Any] = {}
        
        logger.info(f"Gemini client initialized with model: {settings.gemini_model}")
    
    async def generate_json(
        self,
        prompt: str,
        temperature: float = 0.7,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Generate JSON response from Gemini with retry logic.
        
        Args:
            prompt: The prompt to send to Gemini
            temperature: Sampling temperature (0.0-1.0)
            timeout: Request timeout in seconds
            
        Returns:
            Parsed JSON response
            
        Raises:
            Exception: If all retries fail or JSON parsing fails
        """
        # Check demo cache
        if self.demo_mode:
            cache_key = self._get_cache_key(prompt, temperature)
            if cache_key in self._demo_cache:
                logger.info("Returning cached response (demo mode)")
                return self._demo_cache[cache_key]
        
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Gemini API call attempt {attempt}/{self.max_retries}")
                
                # Configure generation parameters
                generation_config = genai.GenerationConfig(
                    temperature=temperature,
                    response_mime_type="application/json"
                )
                
                # Generate response with longer timeout
                # Use max of provided timeout or 60 seconds
                actual_timeout = max(timeout, 60)
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    request_options={"timeout": actual_timeout}
                )
                
                # Extract text
                response_text = response.text
                logger.debug(f"Raw response length: {len(response_text)} chars")
                
                # Parse JSON
                result = self._parse_json(response_text)
                
                # Cache in demo mode
                if self.demo_mode:
                    cache_key = self._get_cache_key(prompt, temperature)
                    self._demo_cache[cache_key] = result
                
                logger.info("Successfully generated and parsed JSON response")
                return result
                
            except json.JSONDecodeError as e:
                last_error = f"JSON parsing error: {str(e)}"
                logger.warning(f"Attempt {attempt} failed: {last_error}")
                
                if attempt < self.max_retries:
                    # Retry with stricter prompt
                    prompt = self._add_json_emphasis(prompt)
                    time.sleep(1)
                    
            except Exception as e:
                last_error = f"API error: {str(e)}"
                logger.warning(f"Attempt {attempt} failed: {last_error}")
                
                if attempt < self.max_retries:
                    # Exponential backoff, longer for timeout errors
                    if "timeout" in str(e).lower() or "504" in str(e):
                        wait_time = 5 * attempt
                        logger.info(f"Timeout detected, waiting {wait_time}s before retry")
                    else:
                        wait_time = 2 * attempt
                    time.sleep(wait_time)
        
        # All retries failed
        error_msg = f"Failed after {self.max_retries} attempts. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """
        Parse JSON from response text, handling common issues.
        
        Args:
            text: Raw response text
            
        Returns:
            Parsed JSON object
            
        Raises:
            json.JSONDecodeError: If parsing fails
        """
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        # Parse JSON
        return json.loads(text)
    
    def _add_json_emphasis(self, prompt: str) -> str:
        """Add stronger JSON formatting requirements to prompt."""
        emphasis = "\n\nIMPORTANT: You MUST return ONLY valid JSON. No markdown, no code blocks, no explanations. Just the raw JSON object."
        if emphasis not in prompt:
            return prompt + emphasis
        return prompt
    
    def _get_cache_key(self, prompt: str, temperature: float) -> str:
        """Generate cache key for demo mode."""
        # Use first 100 chars of prompt + temperature as key
        return f"{prompt[:100]}_{temperature}"
