"""UTCP-to-MCP Bridge for Claude Code."""

import asyncio
import json
from fastmcp import FastMCP
from utcp.utcp_client import UtcpClient

# Initialize FastMCP server
mcp = FastMCP("FINRA UTCP Server")

_utcp_client = None

async def get_utcp_client():
    global _utcp_client
    if _utcp_client is None:
        _utcp_client = await UtcpClient.create(config={
            "manual_call_templates": [
                {
                    "name": "finra_provider",
                    "call_template_type": "file",
                    "file_path": r"C:\Agents\UTCP\finra_manual.json",
                    "allowed_communication_protocols": ["file", "http"]
                }
            ]
        })
    return _utcp_client

@mcp.tool()
async def search_finra_individual(query: str, includePrevious: bool = True, nrows: int = 3) -> str:
    """Search for financial brokers and investment professionals on FINRA BrokerCheck by CRD number or name.
    
    Args:
        query: The individual's CRD number or name search query (e.g., '4455114').
        includePrevious: Whether to include previous employment histories.
        nrows: Number of records to return.
    """
    client = await get_utcp_client()
    
    # Execute tool via UTCP
    result = await client.call_tool(
        tool_name="finra_provider.search_individual",
        tool_args={
            "query": query,
            "includePrevious": "true" if includePrevious else "false",
            "nrows": nrows
        }
    )
    return json.dumps(result, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    mcp.run()