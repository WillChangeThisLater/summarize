from abc import ABC, abstractmethod
from PIL import Image
import asyncio

class BaseLLMClient(ABC):
    _instance = None
    _semaphore: asyncio.Semaphore

    @abstractmethod
    async def chunk(self, text: str) -> list[str]:
        """Divide text into manageable chunks."""
        pass

    @abstractmethod
    async def summarize_text(self, content: str) -> str:
        """Summarize the given text content."""
        pass

    @abstractmethod
    async def summarize_image(self, image: Image) -> str:
        """Generate a summary of the given image content."""
        pass
