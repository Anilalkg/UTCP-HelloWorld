import asyncio
import json
from utcp.utcp_client import UtcpClient
##

async def main():
    print("1. Initializing UTCP Client and loading the local manual...")
    
    client = await UtcpClient.create(config={
        "manual_call_templates": [
            {
                "name": "finra_provider",
                "call_template_type": "file",
                "file_path": "./finra_manual.json",
                "allowed_communication_protocols": ["file", "http"]
            }
        ]
    })

    try:
        print("2. Manual loaded successfully!")

        print("3. Executing end-to-end live tool call to FINRA BrokerCheck...")
        # Pass tool parameters directly as keyword arguments matching your JSON schema
        # result = await client.call_tool(
        #     tool_name="finra_provider.search_individual",
        #     query="4455114",
        #     includePrevious=True,
        #     nrows=3
        # )

        result = await client.call_tool(
            tool_name="finra_provider.search_individual",
            tool_args={
                "query": "4455114",
                "includePrevious": "true",
                "nrows": 3
            }
        )


        print("\n4. Test Results Received Successfully!")
        print("--------------------------------------------------")
        # print(result)
        print(json.dumps(result, indent=2))
        print("--------------------------------------------------")

    except Exception as e:
        print(f"❌ Error during execution: {e}")
        
    finally:
        await client.close()
        print("5. Client connection closed cleanly.")

if __name__ == "__main__":
    asyncio.run(main())