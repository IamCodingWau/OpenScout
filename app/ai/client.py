import httpx
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_URL).rstrip("/")
        self.model = model or settings.MODEL_NAME

    async def check_health(self) -> Dict[str, Any]:
        """Check if Ollama is running and whether the selected model is installed."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    model_found = any(self.model in m for m in models)
                    return {
                        "available": True,
                        "model": self.model,
                        "installed_models": models,
                        "model_ready": model_found,
                        "status": "connected" if model_found else f"Model '{self.model}' not found in Ollama. Run: ollama pull {self.model}"
                    }
        except Exception as e:
            pass

        return {
            "available": False,
            "model": self.model,
            "model_ready": False,
            "status": f"Ollama not reachable at {self.base_url}. Please start Ollama or install via https://ollama.com"
        }

    async def generate(self, prompt: str, system: Optional[str] = None, format: Optional[str] = "json") -> str:
        """Call Ollama /api/generate with fast connection check."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
            }
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format

        # connect timeout 1.5s, read timeout 45s
        timeout = httpx.Timeout(45.0, connect=1.5)
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{self.base_url}/api/generate", json=payload)
            res.raise_for_status()
            data = res.json()
            return data.get("response", "")