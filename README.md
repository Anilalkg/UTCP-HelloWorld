# UTCP FINRA BrokerCheck Agent

An end-to-end, zero-middleware LLM agent powered by the **Universal Tool Calling Protocol (UTCP)** and **Anthropic's Claude** (hosted via Azure AI Foundry).

This project demonstrates how an LLM agent can dynamically discover, execute, and synthesize live production REST API calls—specifically querying the **FINRA BrokerCheck API**—without requiring wrapper HTTP servers, intermediate proxies, or custom API client code.

---

## 💡 What is UTCP?

The **Universal Tool Calling Protocol (UTCP)** is an open standard designed to allow Large Language Models (LLMs) and AI agents to discover, understand, and invoke external tools and APIs in a standardized, schema-driven manner without requiring custom wrapper code or middle-tier proxy servers.

Rather than hardcoding specific API client libraries or writing custom middleware for every service an agent needs to touch, UTCP relies on **declarative tool manuals** (typically JSON or YAML files). These manuals define endpoints, parameters, authentication schemes, and communication protocols (such as standard file execution, HTTP/REST, SSE, or streamable HTTP). An LLM agent can parse these manuals at runtime, understand how to construct valid calls, and execute them natively against live production endpoints.

---

## ⚖️ UTCP vs. MCP: How They Differ

While both **UTCP (Universal Tool Calling Protocol)** and **MCP (Model Context Protocol, pioneered by Anthropic)** aim to standardize how AI models interact with external data sources and tools, their architectural philosophies and target use cases are fundamentally different.

| Feature / Dimension      | Universal Tool Calling Protocol (UTCP)                                                                                                                                       | Model Context Protocol (MCP)                                                                                                                                                                                |
| :----------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Primary Philosophy**   | **API-Centric / Declarative:** Focuses on turning _any existing REST API or script_ into an LLM-ready tool via declarative schemas (manuals) without custom server wrappers. | **Server-Centric / Stateful:** Focuses on establishing a standardized client-server runtime communication protocol (often over stdio or SSE) where servers expose resources, prompts, and tools.            |
| **Execution Model**      | **Direct & Zero-Middleware:** The agent client reads the manual and executes raw protocol calls (like direct HTTP requests) straight to the target endpoint.                 | **Client-Server Architecture:** Requires a dedicated MCP server running locally or remotely that acts as a middle-layer bridge between the host application and the data source.                            |
| **Integration Overhead** | Extremely low for existing APIs—you simply write a JSON/YAML manual describing the API endpoints and parameters.                                                             | Low to moderate—requires implementing a server (using MCP SDKs in Python, TypeScript, etc.) that registers handlers for resources and tools.                                                                |
| **Protocol Support**     | Built-in support for multiple communication protocols out of the box (e.g., `file`, `http`, `sse`, `streamable_http`).                                                       | Standardized primarily around `stdio` transport for local execution and SSE for remote client-server connections.                                                                                           |
| **Best Suited For**      | Connecting LLM agents directly to third-party web APIs, microservices, and databases using declarative specifications.                                                       | Building rich, stateful integrations for IDEs, developer tools, and desktop AI clients (like Claude Desktop or Claude Code) that require file system access, database querying, and live context streaming. |

### Key Takeaway

- **UTCP** acts as a **universal translator for web APIs**, allowing you to point an agent at a schema manual file and immediately execute live HTTP operations directly.
- **MCP** acts as a **standardized runtime bridge for AI clients**, creating a structured, persistent client-server protocol for managing prompts, resources, and local tools.

---

## 🌟 Key Features

- **Universal Tool Calling Protocol (UTCP):** Declarative, schema-driven tool execution directly from a local JSON manual (`finra_manual.json`).
- **Zero-Middleware Architecture:** Eliminates custom wrapper APIs—Claude invokes tools via UTCP, which executes raw, native HTTP requests straight to live production endpoints.
- **Azure AI Foundry Integration:** Native integration with Azure-hosted Claude models (`claude-haiku-5-5`, `claude-3-5-sonnet`, etc.).
- **Model Context Protocol (MCP) Ready:** Includes a `FastMCP` wrapper to effortlessly expose UTCP tools directly into **Claude Code CLI** or desktop AI clients over `stdio`.
- **Multi-Turn Synthesis:** Intercepts Claude's tool invocation requests, resolves parameter types, calls FINRA live, and feeds raw data back to Claude for human-readable synthesis.

---

## 📁 Repository Structure

```text
.
├── finra_manual.json         # UTCP Manual defining the FINRA BrokerCheck tool schema
├── claude_utcp_agent_1.py    # Main agent script (Azure AI Foundry + UTCP + Claude)
├── finra_utcp_mcp.py        # FastMCP server wrapper for Claude Code CLI integration
├── requirements.txt          # Python dependencies
├── .env.example              # Sample environment configuration file
└── README.md                 # Project documentation
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites

- **Python 3.10+** (Tested on Python 3.13)
- An active **Azure AI Foundry** deployment running an Anthropic Claude model.

### 2. Installation & Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/your-username/utcp-finra-agent.git
   cd utcp-finra-agent
   ```

2. **Create and Activate a Virtual Environment:**
   - **Linux/macOS:**
     ```bash
     python3 -m venv utcp-env
     source utcp-env/bin/activate
     ```
   - **Windows (PowerShell):**
     ```powershell
     python -m venv utcp-env
     .\utcp-env\Scripts\Activate.ps1
     ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   ANTHROPIC_API_KEY=your_azure_ai_api_key
   AZURE_AI_ENDPOINT=https://<your-resource-name>.services.ai.azure.com/anthropic
   AZURE_CLAUDE_DEPLOYMENT=claude-haiku-5-5
   ```

---

## 💻 Usage

### Running the Standalone Agent Script

Execute the complete end-to-end agentic loop:

```bash
python claude_utcp_agent_1.py
```

#### What Happens Under the Hood:

1. **Initializes UTCP Client:** Reads `finra_manual.json` and registers the `finra_provider.search_individual` tool.
2. **Sends Prompt to Claude:** Asks Claude to look up a broker by CRD number (e.g., `4455114`).
3. **Tool Call Interception:** Claude triggers `finra_provider_search_individual`.
4. **Direct API Call:** UTCP makes a live HTTPS GET request directly to FINRA's production API.
5. **Synthesis:** UTCP returns the JSON payload back to Claude, which formats a clean summary in your terminal.

---

## 🔌 Running with Claude Code CLI (via MCP)

You can expose this UTCP tool directly to **Claude Code CLI** using Model Context Protocol (MCP).

1. **Add the MCP Server to Claude Code:**

   ```bash
   claude mcp add finra-utcp -- python ./finra_utcp_mcp.py
   ```

2. **Launch Claude Code and Query:**

   ```bash
   claude
   ```

   _Prompt inside Claude Code:_

   > "Search for broker CRD 4455114 on FINRA BrokerCheck and summarize their current registration status."

   > "Can you find details for Bradford Schreck using the FINRA tool?"

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to fork this repository and submit a pull request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.
