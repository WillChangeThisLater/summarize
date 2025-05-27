import asyncio
import io
import logging
import json
from openai import AsyncOpenAI
from datetime import datetime
from PIL import Image
import base64
from typing import Union, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# TODO: move this to more generic models module
class StructuredOutput(BaseModel):
    author: Optional[str]
    publish_date: Optional[str]
    content_type: str
    language: str
    tags: list[str]
    summary: str

    def summarize(self) -> str:
        # Generate a markdown string summarizing the attributes
        author_str = f"**Author:** {self.author}" if self.author else "**Author:** Not specified"
        publish_date_str = f"**Publish Date:** {self.publish_date}" if self.publish_date else "**Publish Date:** Not specified"
        tags_str = ", ".join(self.tags)

        markdown_summary = (
            f"### Summary\n\n"
            f"{author_str}\n\n"
            f"{publish_date_str}\n\n"
            f"**Content Type:** {self.content_type}\n\n"
            f"**Language:** {self.language}\n\n"
            f"**Tags:** {tags_str}\n\n"
            f"**Summary:** {self.summary}\n"
        )
        return markdown_summary

class OpenAIClient():
    _instance = None
    _semaphore = asyncio.Semaphore(5)

    def __new__(cls, model_id: str = "gpt-4o-mini"):
        if cls._instance is None:
            cls._instance = super(OpenAIClient, cls).__new__(cls)
            cls._instance.model_id = model_id
        return cls._instance

    async def chunk(self, text: str) -> list[str]:
        token_size = 8192
        chunks = [text[i:i+token_size] for i in range(0, len(text), token_size)]
        return [chunks[0]]  # Process only the first chunk for efficiency

    async def summarize_text(self, content: str) -> str:
        return await self._handle_summary(content, "text")

    async def summarize_image(self, image: Image) -> str:
        return await self._handle_summary(image, "image")

    async def _handle_summary(self, content: Union[str, Image], data_type: str) -> str:
        client = AsyncOpenAI()

        example_output = {
            "author": "John Doe",  # Example author name
            "publish_date": datetime.today().strftime("%Y-%m-%d"),
            "content_type": data_type,
            "language": "en",
            "tags": ["example", "demo"],
            "summary": "This content discusses the implementation of structured summaries in AI models."
        }
        prompt = f"""
        You are a content summarizer. When given {data_type} data, you should extract relevant details to create structured summaries.
        The output should be in the following JSON format:

        {json.dumps(example_output, indent=4)}
        """

        async with self._semaphore:
            try:
                if data_type == "text":
                    input_data = [
                        {"role": "system", "content": f"You are a summarization tool. Summarize the following text and provide structured output."},
                        {"role": "user", "content": content}
                    ]
                elif data_type == "image":
                    buffered = io.BytesIO()
                    content.save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    input_data = [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": {"image_url": f"data:image/jpeg;base64,{img_str}"}}
                    ]
                else:
                    raise ValueError("Unsupported data type.")

                response = await client.responses.parse(
                    model=self.model_id,
                    input=input_data,
                    text_format=StructuredOutput
                )

                # Assuming the response contains JSON-like structured data.
                result: StructuredOutput = response.output_parsed
                return result.summarize()
            except Exception as e:
                logger.error(f"Error processing {data_type} relevance: {e}")
                raise
