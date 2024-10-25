from typing import Dict, Any, Optional
import requests
import time
from dataclasses import dataclass
from datetime import datetime

from ..core.config import ApiConfig, AppConfig
from ..core.exceptions import ApiError, ApiTimeoutError, ApiResponseError

@dataclass
class ApiResponse:
    """Container for API response data"""
    content: str
    raw_response: Dict[str, Any]
    timestamp: datetime
    attempts: int
    
class ApiService:
    """Handles communication with the language model API"""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def _prepare_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Prepare the API request payload"""
        return {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "mode": "instruct",
            "max_tokens": kwargs.get('max_tokens', self.config.generation.max_tokens)
        }
    
    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare API request headers"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.config.api.key:
            headers["Authorization"] = f"Bearer {self.config.api.key}"
            
        return headers
    
    def _make_request(self, prompt: str, attempt: int = 1, **kwargs) -> ApiResponse:
        """Make API request with retry logic"""
        payload = self._prepare_payload(prompt, **kwargs)
        headers = self._prepare_headers()
        
        try:
            response = requests.post(
                self.config.api.url,
                json=payload,
                headers=headers,
                timeout=self.config.api.timeout
            )
            
            if response.status_code == 429:  # Rate limit
                if attempt < self.config.api.max_retries:
                    time.sleep(self.config.api.retry_delay * attempt)
                    return self._make_request(prompt, attempt + 1, **kwargs)
                raise ApiError("Rate limit exceeded and max retries reached")
                
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            api_response = ApiResponse(
                content=content,
                raw_response=data,
                timestamp=datetime.now(),
                attempts=attempt
            )
            
            self._last_response = api_response
            return api_response
            
        except requests.Timeout:
            if attempt < self.config.api.max_retries:
                time.sleep(self.config.api.retry_delay * attempt)
                return self._make_request(prompt, attempt + 1, **kwargs)
            raise ApiTimeoutError("Request timed out after all retries")
            
        except requests.RequestException as e:
            if attempt < self.config.api.max_retries:
                time.sleep(self.config.api.retry_delay * attempt)
                return self._make_request(prompt, attempt + 1, **kwargs)
            raise ApiResponseError(
                getattr(e.response, 'status_code', 0),
                str(e)
            )
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using the API"""
        try:
            response = self._make_request(prompt, **kwargs)
            return response.content
        except Exception as e:
            raise ApiError(f"Text generation failed: {str(e)}")
    
    @property
    def last_response(self) -> Optional[ApiResponse]:
        """Get the last API response"""
        return self._last_response