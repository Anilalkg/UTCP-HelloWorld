"""Claude + UTCP + FINRA BrokerCheck agent.

Requires: pip install anthropic python-dotenv utcp
Environment: ANTHROPIC_API_KEY, AZURE_AI_ENDPOINT, AZURE_CLAUDE_DEPLOYMENT
Manual: ./finra_manual.json
"""

import asyncio
import inspect
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


# def get_tools(client):
#     """Get registered tools; support UTCP versions with async list_tools."""
#     return client.list_tools()


def get_tools(client):
    """Get registered tools safely across UTCP versions."""
    # 1. Try public listing methods if any exist
    for meth in ["get_tools", "list_tools", "get_all_tools"]:
        if hasattr(client, meth):
            res = getattr(client, meth)()
            if res:
                return res

    # 2. Inspect common internal tool registry attributes on UtcpClientImplementation
    for attr in ["_tools", "tools", "registry", "_registry"]:
        val = getattr(client, attr, None)
        if val:
            if isinstance(val, dict):
                return list(val.values())
            elif isinstance(val, (list, tuple)):
                return list(val)

    # 3. Deep dive into protocol managers if stored there
    if hasattr(client, "_protocol_manager"):
        pm = client._protocol_manager
        for attr in ["tools", "_tools", "registered_tools"]:
            val = getattr(pm, attr, None)
            if val:
                return list(val.values()) if isinstance(val, dict) else list(val)

    return []


def to_claude_tool(tool):
    name = getattr(tool, "namespaced_name", None) or getattr(tool, "name", None)
    if not name:
        raise ValueError(f"Registered UTCP tool lacks a name: {tool!r}")
    inputs = getattr(tool, "inputs", None)
    if hasattr(inputs, "model_dump"):
        schema = inputs.model_dump(exclude_none=True)
    elif isinstance(inputs, dict):
        schema = inputs
    else:
        raise ValueError(f"Tool {name} lacks a valid input schema")
    if schema.get("type") != "object":
        raise ValueError(f"Tool {name} has a non-object input schema: {schema!r}")
    return {
        "name": name.replace(".", "_"),
        "description": getattr(tool, "description", None) or f"Execute {name}",
        "input_schema": schema,
    }, name


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
        print("2. Reading registered UTCP tools...")
        registered = get_tools(utcp_client)
        if inspect.isawaitable(registered):
            registered = await registered
        if not registered:
            raise RuntimeError("No UTCP tools registered; inspect finra_manual.json")

        claude_tools = []
        name_map = {}
        for tool in registered:
            spec, original_name = to_claude_tool(tool)
            if spec["name"] in name_map:
                raise RuntimeError(f"Tool name collision: {spec['name']}")
            claude_tools.append(spec)
            name_map[spec["name"]] = original_name
            print(f"   {spec['name']} -> {original_name}")

        claude = AnthropicFoundry(api_key=api_key, base_url=endpoint)
        messages = [{"role": "user", "content": USER_PROMPT}]
        print(f"\nUser Prompt: {USER_PROMPT}")
        print(f"Claude deployment: {deployment}")

        for round_number in range(1, MAX_ROUNDS + 1):
            print(f"\n3. Claude agent round {round_number}...")
            # AnthropicFoundry is a synchronous client, so use a thread to
            # avoid blocking the async UTCP event loop.
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
                tool_name = name_map.get(block.name)
                print(f"   Claude requested: {block.name} {block.input}")
                if tool_name is None:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Unknown tool: {block.name}",
                        "is_error": True,
                    })
                    continue
                try:
                    tool_args = normalize_utcp_args(block.input)
                    output = await utcp_client.call_tool(
                        tool_name=tool_name, tool_args=tool_args
                    )
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_as_text(output),
                    })
                    print(f"   UTCP tool completed: {tool_name}")
                except Exception as exc:
                    logger.exception("UTCP tool failed: %s", tool_name)
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
