"""Tests for OpenAPI spec operations (schema and endpoint details)."""
from typing import Dict, Any

import pytest

from api_explorer_server.server import get_schema_details, get_endpoint_details


class TestGetSchemaDetails:
    """Tests for get_schema_details function."""

    def test_get_existing_schema(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test getting details for an existing schema."""
        result = get_schema_details(sample_spec_dict, "User")

        assert result["schema_name"] == "User"
        assert "definition" in result
        assert result["definition"]["type"] == "object"
        assert "id" in result["definition"]["properties"]
        assert "name" in result["definition"]["properties"]
        assert "email" in result["definition"]["properties"]

    def test_get_schema_with_required_fields(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that schema details include required fields."""
        result = get_schema_details(sample_spec_dict, "User")

        assert "required" in result["definition"]
        assert "id" in result["definition"]["required"]
        assert "name" in result["definition"]["required"]
        assert "email" in result["definition"]["required"]

    def test_get_schema_with_descriptions(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that schema details include property descriptions."""
        result = get_schema_details(sample_spec_dict, "User")

        properties = result["definition"]["properties"]
        assert properties["id"]["description"] == "User ID"
        assert properties["name"]["description"] == "User's full name"
        assert properties["email"]["description"] == "User's email address"

    def test_get_nonexistent_schema(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test getting a nonexistent schema raises ValueError."""
        with pytest.raises(ValueError, match="Schema 'NonExistent' not found"):
            get_schema_details(sample_spec_dict, "NonExistent")

    def test_get_schema_error_shows_available_schemas(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that error message shows available schemas."""
        with pytest.raises(ValueError, match="Available schemas: User"):
            get_schema_details(sample_spec_dict, "Missing")

    def test_get_schema_from_empty_spec(self, empty_spec_dict: Dict[str, Any]) -> None:
        """Test getting schema from spec with no schemas."""
        # Add empty components to avoid KeyError
        empty_spec_dict["components"] = {"schemas": {}}

        with pytest.raises(ValueError, match="not found"):
            get_schema_details(empty_spec_dict, "AnySchema")


class TestGetEndpointDetails:
    """Tests for get_endpoint_details function."""

    def test_get_existing_endpoint(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test getting details for an existing endpoint."""
        result = get_endpoint_details(sample_spec_dict, "/users", "GET")

        assert result["path"] == "/users"
        assert result["method"] == "GET"
        assert result["summary"] == "Get all users"
        assert result["operationId"] == "getUsers"

    def test_get_endpoint_with_path_parameter(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test getting endpoint with path parameters."""
        result = get_endpoint_details(sample_spec_dict, "/users/{id}", "GET")

        assert result["path"] == "/users/{id}"
        assert result["method"] == "GET"
        assert "parameters" in result
        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["name"] == "id"
        assert result["parameters"][0]["in"] == "path"
        assert result["parameters"][0]["required"] is True

    def test_get_endpoint_post_method(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test getting POST endpoint details."""
        result = get_endpoint_details(sample_spec_dict, "/users", "POST")

        assert result["method"] == "POST"
        assert result["summary"] == "Create a user"
        assert "requestBody" in result
        assert result["requestBody"]["required"] is True

    def test_get_endpoint_case_insensitive_method(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that HTTP method is case-insensitive."""
        result_lower = get_endpoint_details(sample_spec_dict, "/users", "get")
        result_upper = get_endpoint_details(sample_spec_dict, "/users", "GET")
        result_mixed = get_endpoint_details(sample_spec_dict, "/users", "GeT")

        assert result_lower["method"] == "GET"
        assert result_upper["method"] == "GET"
        assert result_mixed["method"] == "GET"

    def test_get_endpoint_includes_servers(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that endpoint details include server information."""
        result = get_endpoint_details(sample_spec_dict, "/users", "GET")

        assert "servers" in result
        assert len(result["servers"]) > 0
        assert result["servers"][0]["url"] == "https://api.test.com/v1"

    def test_get_nonexistent_path(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test getting a nonexistent path raises ValueError."""
        with pytest.raises(ValueError, match="Path '/nonexistent' not found"):
            get_endpoint_details(sample_spec_dict, "/nonexistent", "GET")

    def test_get_nonexistent_method(self, sample_spec_dict: Dict[str, Any]) -> None:
        """Test getting a nonexistent method raises ValueError."""
        with pytest.raises(ValueError, match="Method 'DELETE' not found"):
            get_endpoint_details(sample_spec_dict, "/users", "DELETE")

    def test_get_method_error_shows_available_methods(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that error message shows available methods."""
        with pytest.raises(ValueError, match="Available: GET, POST"):
            get_endpoint_details(sample_spec_dict, "/users", "DELETE")

    def test_get_endpoint_with_responses(
        self, sample_spec_dict: Dict[str, Any]
    ) -> None:
        """Test that endpoint details include response information."""
        result = get_endpoint_details(sample_spec_dict, "/users/{id}", "GET")

        assert "responses" in result
        assert "200" in result["responses"]
        assert "404" in result["responses"]
        assert result["responses"]["200"]["description"] == "Successful response"
        assert result["responses"]["404"]["description"] == "User not found"
