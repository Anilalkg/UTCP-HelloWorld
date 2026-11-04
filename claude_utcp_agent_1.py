"""Claude + UTCP + FINRA BrokerCheck agent.

Requires: pip install anthropic python-dotenv utcp
Environment: ANTHROPIC_API_KEY, AZURE_AI_ENDPOINT, AZURE_CLAUDE_DEPLOYMENT
Manual: ./finra_manual.json
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from anthropic import AnthropicFoundry
from utcp.utcp_client import UtcpClient

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MANUAL_PATH = Path(__file__).resolve().parent / "finra_manual.json"
MAX_ROUNDS = 8
USER_PROMPT = (
    "Can you look up broker CRD number 4455114 on FINRA BrokerCheck "
    "and tell me their name and employment history?"
)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def normalize_utcp_args(args):
    """UTCP HTTP template substitution rejects bools; stringify at boundary."""
    normalized = dict(args)
    if isinstance(normalized.get("includePrevious"), bool):
        normalized["includePrevious"] = (
            "true" if normalized["includePrevious"] else "false"
        )
    return normalized


def result_as_text(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


async def main():
    api_key = required_env("ANTHROPIC_API_KEY")
    endpoint = required_env("AZURE_AI_ENDPOINT")
    deployment = required_env("AZURE_CLAUDE_DEPLOYMENT")

    if not MANUAL_PATH.is_file():
        raise FileNotFoundError(f"FINRA UTCP manual not found: {MANUAL_PATH}")

    print("1. Initializing UTCP Client and loading FINRA manual...")
    utcp_client = await UtcpClient.create(config={
        "manual_call_templates": [
            {
                "name": "finra_provider",
                "call_template_type": "file",
                "file_path": str(MANUAL_PATH),
                "allowed_communication_protocols": ["file", "http"],
            }
        ]
    })

    try:
        print("2. Configuring Claude tool definitions...")
        # Define the tool explicitly based on your finra_manual.json schema
        claude_tools = [
            {
                "name": "finra_provider_search_individual",
                "description": "Search for financial brokers and investment professionals by CRD number or name query.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The individual's CRD number or name query (e.g., '4455114')."
                        },
                        "includePrevious": {
                            "type": "boolean",
                            "description": "Whether to include previous employment/history records."
                        },
                        "nrows": {
                            "type": "integer",
                            "description": "Number of records to return."
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
        
        original_tool_name = "finra_provider.search_individual"
        print(f"   Registered tool: finra_provider_search_individual -> {original_tool_name}")

        claude = AnthropicFoundry(api_key=api_key, base_url=endpoint)
        messages = [{"role": "user", "content": USER_PROMPT}]
        print(f"\nUser Prompt: {USER_PROMPT}")
        print(f"Claude deployment: {deployment}")

        for round_number in range(1, MAX_ROUNDS + 1):
            print(f"\n3. Claude agent round {round_number}...")
            # AnthropicFoundry is synchronous, run in thread to keep async event loop clear
            response = await asyncio.to_thread(
                claude.messages.create,
                model=deployment,
                max_tokens=2048,
                tools=claude_tools,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})
            tool_blocks = [block for block in response.content if block.type == "tool_use"]

            if not tool_blocks:
                print("\n--- Final Claude Answer ---")
                for block in response.content:
                    if block.type == "text":
                        print(block.text)
                if response.stop_reason != "end_turn":
                    print(f"\nWarning: Claude stopped with reason {response.stop_reason!r}")
                return

            results = []
            for block in tool_blocks:
                print(f"   Claude requested: {block.name} with inputs {block.input}")
                try:
                    tool_args = normalize_utcp_args(block.input)
                    output = await utcp_client.call_tool(
                        tool_name=original_tool_name, tool_args=tool_args
                    )
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_as_text(output),
                    })
                    print(f"   UTCP tool completed successfully: {original_tool_name}")
                except Exception as exc:
                    logger.exception("UTCP tool failed: %s", original_tool_name)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Tool execution failed: {exc}",
                        "is_error": True,
                    })
            messages.append({"role": "user", "content": results})

        print(f"Agent stopped after {MAX_ROUNDS} rounds (safety limit).")

    finally:
        await utcp_client.close()
        print("\nUTCP client connections closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("Agent execution failed: %s", exc)