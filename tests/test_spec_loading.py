"""Tests for OpenAPI spec loading functionality."""
from pathlib import Path
from typing import Dict, Any

import pytest
from pytest_httpx import HTTPXMock

from api_explorer_server.server import load_openapi_spec, summarize_openapi_spec


class TestLoadOpenAPISpec:
    """Tests for load_openapi_spec function."""

    def test_load_json_file(
        self, sample_spec_json_path: Path, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test loading OpenAPI spec from a JSON file."""
        spec = load_openapi_spec(str(sample_spec_json_path))

        assert spec == sample_spec_dict
        assert spec["openapi"] == "3.0.0"
        assert spec["info"]["title"] == "Test API"

    def test_load_yaml_file(self, sample_spec_yaml_path: Path) -> None:
        """Test loading OpenAPI spec from a YAML file."""
        spec = load_openapi_spec(str(sample_spec_yaml_path))

        assert spec["openapi"] == "3.0.0"
        assert spec["info"]["title"] == "Test API YAML"
        assert "/products" in spec["paths"]

    def test_load_from_http_url(self, httpx_mock: HTTPXMock) -> None:
        """Test loading OpenAPI spec from an HTTP URL."""
        mock_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Remote API", "version": "1.0.0"},
            "paths": {},
        }

        httpx_mock.add_response(
            url="http://example.com/openapi.json",
            json=mock_spec,
        )

        spec = load_openapi_spec("http://example.com/openapi.json")

        assert spec == mock_spec
        assert spec["info"]["title"] == "Remote API"

    def test_load_from_https_url(self, httpx_mock: HTTPXMock) -> None:
        """Test loading OpenAPI spec from an HTTPS URL."""
        mock_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Secure API", "version": "1.0.0"},
            "paths": {},
        }

        httpx_mock.add_response(
            url="https://secure.example.com/openapi.yaml",
            text="openapi: 3.0.0\ninfo:\n  title: Secure API\n  version: 1.0.0\npaths: {}",
        )

        spec = load_openapi_spec("https://secure.example.com/openapi.yaml")

        assert spec["info"]["title"] == "Secure API"

    def test_load_nonexistent_file(self) -> None:
        """Test loading a nonexistent file raises FileNotFoundError."""
        with pytest.raises(Exception, match="File not found"):
            load_openapi_spec("/nonexistent/path/to/spec.json")

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON raises an exception."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        with pytest.raises(Exception, match="Failed to load OpenAPI spec"):
            load_openapi_spec(str(invalid_file))

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        """Test loading invalid YAML raises an exception."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: [yaml: content")

        with pytest.raises(Exception, match="Failed to load OpenAPI spec"):
            load_openapi_spec(str(invalid_file))

    def test_load_http_error(self, httpx_mock: HTTPXMock) -> None:
        """Test loading from URL with HTTP error."""
        httpx_mock.add_response(
            url="http://example.com/notfound.json",
            status_code=404,
        )

        with pytest.raises(Exception, match="Failed to load OpenAPI spec"):
            load_openapi_spec("http://example.com/notfound.json")


class TestSummarizeOpenAPISpec:
    """Tests for summarize_openapi_spec function."""

    def test_summarize_basic_spec(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test summarizing a basic OpenAPI spec."""
        summary = summarize_openapi_spec(sample_spec_dict)

        assert "API: Test API" in summary
        assert "Version: 1.0.0" in summary
        assert "Description: A test API for unit tests" in summary

    def test_summarize_includes_servers(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test that summary includes server information."""
        summary = summarize_openapi_spec(sample_spec_dict)

        assert "SERVERS" in summary
        assert "https://api.test.com/v1" in summary

    def test_summarize_includes_endpoints(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that summary includes endpoint information."""
        summary = summarize_openapi_spec(sample_spec_dict)

        assert "ENDPOINTS" in summary
        assert "GET /users" in summary
        assert "POST /users" in summary
        assert "GET /users/{id}" in summary

    def test_summarize_includes_schemas(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test that summary includes schema information."""
        summary = summarize_openapi_spec(sample_spec_dict)

        assert "SCHEMAS" in summary
        assert "User" in summary

    def test_summarize_empty_spec(self, empty_spec_dict: Dict[str, Any]) -> None:
        """Test summarizing an empty but valid spec."""
        summary = summarize_openapi_spec(empty_spec_dict)

        assert "API: Empty API" in summary
        assert "Version: 1.0.0" in summary
        assert "ENDPOINTS (0 paths)" in summary

    def test_summarize_includes_overview_tags(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that summary includes overview tag descriptions."""
        summary = summarize_openapi_spec(sample_spec_dict)

        assert "API OVERVIEW & USAGE INSTRUCTIONS" in summary
        assert "Overview" in summary

    def test_summarize_cleans_html_in_tag_descriptions(self) -> None:
        """Test that HTML tags are cleaned from tag descriptions."""
        spec_with_html = {
            "openapi": "3.0.0",
            "info": {
                "title": "HTML API",
                "version": "1.0.0",
                "description": "Plain description",
            },
            "tags": [
                {
                    "name": "Overview",
                    "description": "<h3>Header</h3><p>Some <br>content</p><b>Bold text</b>",
                }
            ],
            "paths": {},
        }

        summary = summarize_openapi_spec(spec_with_html)

        # Check that HTML tags are cleaned from tag descriptions
        overview_section = summary.split("API OVERVIEW")[1] if "API OVERVIEW" in summary else ""
        assert "<h3>" not in overview_section
        assert "<p>" not in overview_section
        assert "<b>" not in overview_section
        assert "Header" in overview_section
        assert "Bold text" in overview_section
