"""Tests for MCP server integration."""
from api_explorer_server.server import create_server


class TestServerCreation:
    """Tests for MCP server creation."""

    def test_create_server_returns_server_instance(self) -> None:
        """Test that create_server returns a server instance."""
        server = create_server()

        assert server is not None
        assert hasattr(server, "name")
        assert server.name == "mcp-api-explorer"
