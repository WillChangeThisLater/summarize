import aiofiles
import argparse
import asyncio
import httpx
import logging
import os
import sys
from urllib.parse import urlparse, urlsplit, parse_qs
from atlassian import Confluence, Jira
from PIL import Image

from summarize.clients.base import BaseLLMClient
from summarize.clients.openai import OpenAIClient

logger = logging.getLogger(__name__)

# Function to handle the reading of URIs
async def read_uris_from_stdin() -> list[str]:
    uris = [line.strip() for line in sys.stdin]
    return uris

async def read_uris_from_file(file_path: str) -> list[str]:
    async with aiofiles.open(file_path, mode='r') as file:
        contents = await file.readlines()
    return [line.strip() for line in contents]

# Function to summarize different types of URIs
async def summarize_uri(client: BaseLLMClient, uri: str) -> str:
    if uri.startswith("http"):
        if "atlassian" in uri:
            return await summarize_atlassian(client, uri)
        return await summarize_url(client, uri)
    elif os.path.isdir(uri):
        return await summarize_directory(client, uri)
    elif uri.lower().endswith(('.jpg', '.jpeg', '.png')):
        return await summarize_image(client, uri)
    else:
        return await summarize_text_file(client, uri)

async def summarize_atlassian(client: BaseLLMClient, uri: str) -> str:
    """Summarize content from Atlassian resources (JIRA tickets, Confluence pages)."""
    parsed_uri = urlparse(uri)
    atlassian_url = parsed_uri.netloc
    username, password = os.environ["CONFLUENCE_API_USERNAME"], os.environ["CONFLUENCE_API_KEY"]

    if "/browse/" in parsed_uri.path:
        jira_client = Jira(url=f'https://{atlassian_url}', username=username, password=password, cloud=True)
        ticket_id = uri.split('/')[-1]
        ticket = jira_client.issue(ticket_id)
        content = f"{ticket['fields']['summary']} {ticket['fields']['description']}"
        if 'comments' in ticket['fields']:
            content += ' '.join(comment['body'] for comment in jira_client.issue_get_comments(ticket_id)['comments'])
        return await client.summarize_text(content)

    elif "/wiki/spaces/" in parsed_uri.path:
        confluence_client = Confluence(url=f'https://{atlassian_url}', username=username, password=password, cloud=True)
        if "pages" in parsed_uri.path:
            page_id = uri.split('/')[-1]
            page_content = confluence_client.get_page_by_id(page_id, expand='body.storage')['body']['storage']['value']
        else:
            space_key = parsed_uri.path.split('/')[3]
            pages = confluence_client.get_all_pages_from_space(space_key, start=0, limit=100, expand='body.storage', content_type='page')
            page_content = ' '.join(page['body']['storage']['value'] for page in pages)
        return await client.summarize_text(page_content)

async def summarize_url(client: BaseLLMClient, uri: str) -> str:
    async with httpx.AsyncClient() as httpx_client:
        response = await httpx_client.get(uri)
        response.raise_for_status()
        return await client.summarize_text(response.text)

async def summarize_directory(client: BaseLLMClient, directory: str) -> list[str]:
    summaries = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            summary = await summarize_uri(client, file_path)
            summaries.append(summary)
    return "\n".join(summaries)

async def summarize_text_file(client: BaseLLMClient, file_name: str) -> str:
    async with aiofiles.open(file_name, mode="r", encoding="utf-8", errors="ignore") as fp:
        contents = await fp.read()
    return await client.summarize_text(contents)

async def summarize_image(client: BaseLLMClient, file_name: str) -> str:
    with Image.open(file_name) as image:
        return await client.summarize_image(image)

# Function to handle concurrency using semaphore
async def handle_uri_semaphore(semaphore: asyncio.Semaphore, client: BaseLLMClient, uri: str) -> tuple[str, str]:
    async with semaphore:
        summary = await summarize_uri(client, uri)
        return uri, summary

# CLI function
async def cli():
    parser = argparse.ArgumentParser(description="CLI tool to summarize URIs.")
    parser.add_argument('--input', type=str, help="Optional file path containing URIs")
    parser.add_argument('--provider', type=str, default="openai", help="LLM client provider")
    parser.add_argument('--concurrency', type=int, default=10, help="Number of concurrent URIs to process")

    args = parser.parse_args()

    if args.input:
        uris = await read_uris_from_file(args.input)
    else:
        uris = await read_uris_from_stdin()

    # Initialize the LLM client based on the provider argument
    if args.provider == "openai":
        client = OpenAIClient()
    elif args.provider == "bedrock":
        client = BedrockClient()
    else:
        raise NotImplementedError(f"Error - client {args.client} is not implemented")

    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [handle_uri_semaphore(semaphore, client, uri) for uri in uris]
    results = await asyncio.gather(*tasks)

    # Output the summarized content
    for uri, summary in results:
        print(f"URI: {uri}\nSummary:\n{summary}\n")

def main():
    asyncio.run(cli())

if __name__ == "__main__":
    main()
