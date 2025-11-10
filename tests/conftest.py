"""Pytest configuration and fixtures for API Explorer MCP tests."""
import json
from pathlib import Path
from typing import Dict, Any

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_spec_json_path(fixtures_dir: Path) -> Path:
    """Return the path to the sample JSON OpenAPI spec."""
    return fixtures_dir / "sample_openapi.json"


@pytest.fixture
def sample_spec_yaml_path(fixtures_dir: Path) -> Path:
    """Return the path to the sample YAML OpenAPI spec."""
    return fixtures_dir / "sample_openapi.yaml"


@pytest.fixture
def sample_spec_dict(sample_spec_json_path: Path) -> Dict[str, Any]:
    """Return the sample OpenAPI spec as a dictionary."""
    return json.loads(sample_spec_json_path.read_text())


@pytest.fixture
def empty_spec_dict() -> Dict[str, Any]:
    """Return an empty but valid OpenAPI spec."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Empty API", "version": "1.0.0"},
        "paths": {},
    }
