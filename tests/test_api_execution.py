"""Tests for API call execution functionality."""
import pytest
from pytest_httpx import HTTPXMock

from api_explorer_server.server import execute_api_call


class TestExecuteAPICall:
    """Tests for execute_api_call function."""

    async def test_execute_simple_get_request(self, httpx_mock: HTTPXMock) -> None:
        """Test executing a simple GET request."""
        httpx_mock.add_response(
            url="https://api.example.com/users",
            json={"users": [{"id": 1, "name": "John"}]},
        )

        result = await execute_api_call("https://api.example.com/users")

        assert result["status_code"] == 200
        assert result["json"]["users"][0]["name"] == "John"
        assert result["request"]["method"] == "GET"

    async def test_execute_post_request_with_json_body(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test executing a POST request with JSON body."""
        httpx_mock.add_response(
            url="https://api.example.com/users",
            json={"id": 123, "name": "Jane"},
            status_code=201,
        )

        body = {"name": "Jane", "email": "jane@example.com"}
        result = await execute_api_call(
            "https://api.example.com/users", method="POST", body=body
        )

        assert result["status_code"] == 201
        assert result["request"]["method"] == "POST"
        assert result["request"]["body"] == body
        assert result["json"]["name"] == "Jane"

    async def test_execute_with_headers(self, httpx_mock: HTTPXMock) -> None:
        """Test executing request with custom headers."""
        httpx_mock.add_response(
            url="https://api.example.com/secure",
            json={"message": "authorized"},
        )

        headers = {
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value",
        }
        result = await execute_api_call(
            "https://api.example.com/secure", headers=headers
        )

        assert result["status_code"] == 200
        assert result["request"]["headers"]["Authorization"] == "Bearer token123"
        assert result["request"]["headers"]["X-Custom-Header"] == "custom-value"

    async def test_execute_with_query_params(self, httpx_mock: HTTPXMock) -> None:
        """Test executing request with query parameters."""
        httpx_mock.add_response(
            url="https://api.example.com/search?q=test&limit=10",
            json={"results": []},
        )

        params = {"q": "test", "limit": 10}
        result = await execute_api_call(
            "https://api.example.com/search", params=params
        )

        assert result["status_code"] == 200
        assert result["request"]["params"] == params

    async def test_execute_put_request(self, httpx_mock: HTTPXMock) -> None:
        """Test executing a PUT request."""
        httpx_mock.add_response(
            url="https://api.example.com/users/123",
            json={"id": 123, "name": "Updated Name"},
        )

        result = await execute_api_call(
            "https://api.example.com/users/123",
            method="PUT",
            body={"name": "Updated Name"},
        )

        assert result["status_code"] == 200
        assert result["request"]["method"] == "PUT"

    async def test_execute_delete_request(self, httpx_mock: HTTPXMock) -> None:
        """Test executing a DELETE request."""
        httpx_mock.add_response(
            url="https://api.example.com/users/123", status_code=204, text=""
        )

        result = await execute_api_call(
            "https://api.example.com/users/123", method="DELETE"
        )

        assert result["status_code"] == 204
        assert result["request"]["method"] == "DELETE"

    async def test_execute_handles_non_json_response(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test handling non-JSON response."""
        httpx_mock.add_response(
            url="https://api.example.com/text",
            text="Plain text response",
            headers={"Content-Type": "text/plain"},
        )

        result = await execute_api_call("https://api.example.com/text")

        assert result["status_code"] == 200
        assert result["text"] == "Plain text response"
        assert result["json"] is None

    async def test_execute_with_custom_timeout(self, httpx_mock: HTTPXMock) -> None:
        """Test executing request with custom timeout."""
        httpx_mock.add_response(
            url="https://api.example.com/slow", json={"data": "ok"}
        )

        result = await execute_api_call(
            "https://api.example.com/slow", timeout=60.0
        )

        assert result["status_code"] == 200

    async def test_execute_handles_http_errors(self, httpx_mock: HTTPXMock) -> None:
        """Test handling HTTP error responses."""
        httpx_mock.add_response(
            url="https://api.example.com/notfound",
            status_code=404,
            json={"error": "Not found"},
        )

        result = await execute_api_call("https://api.example.com/notfound")

        assert result["status_code"] == 404
        assert result["json"]["error"] == "Not found"

    async def test_execute_handles_network_errors(self) -> None:
        """Test handling network errors."""
        result = await execute_api_call("https://invalid-domain-that-does-not-exist.com")

        assert "error" in result
        assert "request" in result
        assert result["request"]["url"] == "https://invalid-domain-that-does-not-exist.com"

    async def test_execute_with_string_body(self, httpx_mock: HTTPXMock) -> None:
        """Test executing request with string body."""
        httpx_mock.add_response(
            url="https://api.example.com/text", json={"received": "ok"}
        )

        result = await execute_api_call(
            "https://api.example.com/text", method="POST", body="plain text data"
        )

        assert result["status_code"] == 200
        assert result["request"]["body"] == "plain text data"

    async def test_execute_auto_sets_content_type_for_json(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test that Content-Type is auto-set for JSON body."""
        httpx_mock.add_response(
            url="https://api.example.com/json", json={"ok": True}
        )

        result = await execute_api_call(
            "https://api.example.com/json", method="POST", body={"key": "value"}
        )

        assert result["status_code"] == 200
        assert result["request"]["headers"]["Content-Type"] == "application/json"

    async def test_execute_respects_explicit_content_type(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test that explicit Content-Type header is respected."""
        httpx_mock.add_response(
            url="https://api.example.com/custom", json={"ok": True}
        )

        headers = {"Content-Type": "application/x-custom"}
        result = await execute_api_call(
            "https://api.example.com/custom",
            method="POST",
            body={"key": "value"},
            headers=headers,
        )

        assert result["status_code"] == 200

    async def test_execute_includes_response_headers(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test that response includes headers."""
        httpx_mock.add_response(
            url="https://api.example.com/headers",
            json={"ok": True},
            headers={"X-Custom": "value", "X-Rate-Limit": "100"},
        )

        result = await execute_api_call("https://api.example.com/headers")

        assert "headers" in result
        assert "x-custom" in result["headers"]
        assert result["headers"]["x-custom"] == "value"

    async def test_execute_includes_final_url(self, httpx_mock: HTTPXMock) -> None:
        """Test that result includes the final URL."""
        httpx_mock.add_response(
            url="https://api.example.com/endpoint?param=value", json={"ok": True}
        )

        result = await execute_api_call(
            "https://api.example.com/endpoint", params={"param": "value"}
        )

        assert "url" in result
        assert "api.example.com/endpoint" in result["url"]
