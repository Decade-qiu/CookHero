# app/config/mcp_config.py
"""
MCP (Model Context Protocol) configuration for CookHero.
"""

from typing import Optional

from pydantic import BaseModel


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    enabled: bool = True


class MCPConfig(BaseModel):
    """
    Configuration for MCP (Model Context Protocol) integration.
    """

    amap_api_key: Optional[str] = None  # Loaded from .env (AMAP_API_KEY)
    amap: MCPServerConfig = MCPServerConfig()
    parallel_search: MCPServerConfig = MCPServerConfig(enabled=False)
