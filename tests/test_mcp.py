#!/usr/bin/env python3
"""
MCP Test Script

Tests the MCP client and registry functionality.
Run from project root: python -m tests.test_mcp
"""

import asyncio
import importlib.util
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_mcp_client():
    """Test MCP client directly."""
    from app.config import settings
    from app.agent.tools.mcp.client import MCPClient  # noqa: F401

    print("\n" + "=" * 60)
    print("Testing MCP Client")
    print("=" * 60)

    # Check API key
    amap_key = settings.mcp.amap_api_key
    if not amap_key:
        print("ERROR: AMAP_API_KEY not configured!")
        print("Please set AMAP_API_KEY in your .env file")
        return

    print(f"AMAP API Key: {amap_key[:8]}...")

    # Build endpoint - use StreamableHTTP (recommended by Amap)
    endpoint = f"https://mcp.amap.com/mcp?key={amap_key}"
    print(f"Endpoint: {endpoint}")

    # Create client
    client = MCPClient(endpoint)

    try:
        # Initialize
        print("\n--- Initializing MCP session ---")
        init_result = await client.initialize()
        print(f"Initialize result: {init_result}")

        # List tools
        print("\n--- Listing available tools ---")
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(
                f"  - {tool.get('name')}: {tool.get('description', 'No description')[:50]}..."
            )

        # Try calling a tool
        if tools:
            tool_name = tools[0].get("name")
            print(f"\n--- Testing tool call: {tool_name} ---")

            # Find a weather tool or use first tool
            weather_tool = next(
                (t for t in tools if "weather" in t.get("name", "").lower()), None
            )
            if weather_tool:
                print(f"Found weather tool: {weather_tool.get('name')}")
                result = await client.call_tool(
                    weather_tool.get("name") or "", {"city": "苏州"}
                )
                print(f"Result: {result}")

    except Exception as e:
        logger.exception(f"MCP client test failed: {e}")
        print(f"ERROR: {e}")


async def test_mcp_registry():
    """Test MCP provider and tool loading."""
    from app.config import settings
    from app.agent import setup_agent_module
    from app.agent.registry import AgentHub  # noqa: F401
    from app.agent.tools.mcp.setup import register_amap_mcp  # noqa: F401

    print("\n" + "=" * 60)
    print("Testing MCP Registry")
    print("=" * 60)

    # Check if amap is enabled
    print(f"Amap MCP enabled: {settings.mcp.amap.enabled}")
    print(f"Amap API key configured: {bool(settings.mcp.amap_api_key)}")

    # Initialize module (providers + builtin tools + default agent)
    setup_agent_module()

    # Register amap MCP
    print("\n--- Registering Amap MCP ---")
    await register_amap_mcp()

    # List registered servers
    print("\n--- Registered MCP servers ---")
    mcp_provider = AgentHub.get_provider("mcp")
    servers = (
        getattr(mcp_provider, "list_servers")()
        if hasattr(mcp_provider, "list_servers")
        else []
    )
    print(f"Servers: {servers}")

    # List tools for each server
    for server in servers:
        tools = []  # MCP tools are loaded into AgentHub provider
        print(f"Tools from {server}: {tools}")

    # List all registered tools in AgentHub
    print("\n--- All registered tools in AgentHub ---")
    all_tools = AgentHub.list_tools()
    print(f"Total tools: {len(all_tools)}")
    for tool_name in all_tools:
        tool = AgentHub.get_tool(tool_name)
        tool_type = "mcp" if tool_name.startswith("mcp_") else "builtin"
        print(
            f"  - [{tool_type}] {tool_name}: {tool.description[:50] if tool else 'N/A'}..."
        )


async def test_tool_execution():
    """Test executing an MCP tool through the registry."""
    from app.agent.tools.mcp.setup import register_amap_mcp  # noqa: F401
    from app.agent import setup_agent_module
    from app.agent.registry import AgentHub  # noqa: F401

    print("\n" + "=" * 60)
    print("Testing Tool Execution")
    print("=" * 60)

    # Register all tools
    print("--- Initializing agent module ---")
    setup_agent_module()

    print("--- Registering MCP tools ---")
    await register_amap_mcp()

    # Try to find and execute the weather tool
    print("\n--- Looking for weather tool ---")
    all_tools = AgentHub.list_tools()
    weather_tools = [t for t in all_tools if "weather" in t.lower()]
    print(f"Weather-related tools: {weather_tools}")

    if weather_tools:
        tool_name = weather_tools[0]
        tool = AgentHub.get_tool(tool_name)
        if tool:
            print(f"\n--- Executing {tool_name} ---")
            print(f"Tool description: {tool.description}")
            print(f"Tool parameters: {tool.parameters}")

            result = await tool.execute(city="苏州")
            print(f"Result: {result}")
    else:
        print("No weather tools found!")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Test Suite")
    print("=" * 60)

    try:
        # Test 1: Direct client test
        await test_mcp_client()

        # Test 2: Registry test
        await test_mcp_registry()

        # Test 3: Tool execution test
        await test_tool_execution()

    except Exception as e:
        logger.exception(f"Test failed: {e}")
        print(f"\nTest failed with error: {e}")


class TestParallelSearchMCP(IsolatedAsyncioTestCase):
    def load_setup(self, enabled):
        module_name = "cookhero_mcp_setup_test"
        agent_hub = Mock()
        modules = {
            "app.agent.registry": SimpleNamespace(AgentHub=agent_hub),
            "app.agent.tools.providers.mcp": SimpleNamespace(MCPToolProvider=object),
            "app.config": SimpleNamespace(
                settings=SimpleNamespace(
                    mcp=SimpleNamespace(
                        parallel_search=SimpleNamespace(enabled=enabled)
                    )
                )
            ),
        }
        spec = importlib.util.spec_from_file_location(
            module_name, Path(__file__).parents[1] / "app/agent/tools/mcp/setup.py"
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(module)
        return module._register_parallel_search_mcp, agent_hub, modules

    async def test_disabled_does_not_access_provider(self):
        register, agent_hub, modules = self.load_setup(enabled=False)
        with patch.dict(sys.modules, modules):
            await register()
        agent_hub.get_provider.assert_not_called()

    async def test_opted_in_registers_and_loads_tools(self):
        register, agent_hub, modules = self.load_setup(enabled=True)
        provider = Mock(load_server_tools=AsyncMock(return_value=[Mock()]))
        agent_hub.get_provider.return_value = provider
        with patch.dict(sys.modules, modules):
            await register()
        provider.register_server.assert_called_once_with(
            "parallel_search", "https://search.parallel.ai/mcp"
        )
        provider.load_server_tools.assert_awaited_once_with("parallel_search")


if __name__ == "__main__":
    asyncio.run(main())
