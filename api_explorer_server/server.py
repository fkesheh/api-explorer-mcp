import contextlib
import logging
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from collections.abc import AsyncIterator

import anyio
import click
import httpx
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

logger = logging.getLogger(__name__)

# Store for loaded OpenAPI specs (in memory for this session)
loaded_specs: Dict[str, Dict[str, Any]] = {}


def load_openapi_spec(file_path_or_url: str) -> Dict[str, Any]:
    """Load OpenAPI spec from file path or URL."""
    try:
        if file_path_or_url.startswith(('http://', 'https://')):
            # Load from URL
            with httpx.Client() as client:
                response = client.get(file_path_or_url)
                response.raise_for_status()
                content = response.text
        else:
            # Load from file
            path = Path(file_path_or_url)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path_or_url}")
            content = path.read_text()
        
        # Parse content
        if file_path_or_url.lower().endswith(('.yml', '.yaml')) or content.strip().startswith(('openapi:', 'swagger:')):
            return yaml.safe_load(content)
        else:
            return json.loads(content)
    except Exception as e:
        raise Exception(f"Failed to load OpenAPI spec: {str(e)}")


def summarize_openapi_spec(spec: Dict[str, Any]) -> str:
    """Create a summary of the OpenAPI spec showing available endpoints."""
    summary_lines = []
    
    # Basic info
    info = spec.get('info', {})
    summary_lines.append(f"API: {info.get('title', 'Unknown')}")
    summary_lines.append(f"Version: {info.get('version', 'Unknown')}")
    summary_lines.append(f"Description: {info.get('description', 'No description')}")
    
    # Add tag descriptions, especially "Overview" with API usage instructions
    tags = spec.get('tags', [])
    overview_tags = []
    other_important_tags = []
    
    for tag in tags:
        tag_name = tag.get('name', '')
        tag_description = tag.get('description', '')
        
        if tag_name.lower() in ['overview', 'introduction', 'getting started', 'authentication']:
            overview_tags.append((tag_name, tag_description))
        elif tag_description and len(tag_description) > 200:  # Capture other detailed tags
            other_important_tags.append((tag_name, tag_description))
    
    # Include overview/intro information
    if overview_tags:
        summary_lines.append(f"\n{'='*50}")
        summary_lines.append("API OVERVIEW & USAGE INSTRUCTIONS")
        summary_lines.append(f"{'='*50}")
        
        for tag_name, tag_description in overview_tags:
            summary_lines.append(f"\n## {tag_name}")
            # Clean up HTML tags and format the description nicely
            clean_description = _clean_html_description(tag_description)
            summary_lines.append(clean_description)
    
    # Add other important tag descriptions if they contain valuable info
    if other_important_tags and len(other_important_tags) <= 3:  # Don't overwhelm with too many
        summary_lines.append(f"\n{'='*50}")
        summary_lines.append("IMPORTANT CONCEPTS")
        summary_lines.append(f"{'='*50}")
        
        for tag_name, tag_description in other_important_tags[:3]:  # Limit to 3
            summary_lines.append(f"\n## {tag_name}")
            clean_description = _clean_html_description(tag_description)
            # Truncate very long descriptions
            if len(clean_description) > 1000:
                clean_description = clean_description[:1000] + "...\n[See full documentation for complete details]"
            summary_lines.append(clean_description)
    
    # Servers
    servers = spec.get('servers', [])
    if servers:
        summary_lines.append(f"\n{'='*50}")
        summary_lines.append("SERVERS")
        summary_lines.append(f"{'='*50}")
        for server in servers:
            summary_lines.append(f"  - {server.get('url', 'Unknown URL')}: {server.get('description', '')}")
    
    # Endpoints
    paths = spec.get('paths', {})
    summary_lines.append(f"\n{'='*50}")
    summary_lines.append(f"ENDPOINTS ({len(paths)} paths)")
    summary_lines.append(f"{'='*50}")
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                summary = details.get('summary', details.get('operationId', 'No summary'))
                summary_lines.append(f"  {method.upper()} {path} - {summary}")
    
    # Schemas - show all schemas instead of truncating
    components = spec.get('components', {})
    schemas = components.get('schemas', {})
    if schemas:
        summary_lines.append(f"\n{'='*50}")
        summary_lines.append(f"SCHEMAS ({len(schemas)} defined)")
        summary_lines.append(f"{'='*50}")
        for schema_name in schemas.keys():
            summary_lines.append(f"  - {schema_name}")
    
    return "\n".join(summary_lines)


def _clean_html_description(description: str) -> str:
    """Clean HTML tags and format description text for better readability."""
    import re
    
    # Remove HTML tags but keep the content
    # Replace <br> and </br> with newlines
    description = re.sub(r'<br\s*/?>', '\n', description, flags=re.IGNORECASE)
    description = re.sub(r'</br>', '\n', description, flags=re.IGNORECASE)
    
    # Replace <p> tags with double newlines for paragraphs  
    description = re.sub(r'<p[^>]*>', '\n\n', description, flags=re.IGNORECASE)
    description = re.sub(r'</p>', '', description, flags=re.IGNORECASE)
    
    # Replace <h3> and similar headers
    description = re.sub(r'<h([1-6])[^>]*>', r'\n### ', description, flags=re.IGNORECASE)
    description = re.sub(r'</h[1-6]>', '\n', description, flags=re.IGNORECASE)
    
    # Replace <a> tags with their content and URL
    description = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>([^<]*)</a>', r'\2 (\1)', description, flags=re.IGNORECASE)
    
    # Replace <b> and <strong> tags
    description = re.sub(r'<(b|strong)[^>]*>', '**', description, flags=re.IGNORECASE)
    description = re.sub(r'</(b|strong)>', '**', description, flags=re.IGNORECASE)
    
    # Remove other HTML tags
    description = re.sub(r'<[^>]+>', '', description)
    
    # Clean up whitespace
    description = re.sub(r'\n\s*\n\s*\n', '\n\n', description)  # Multiple newlines to double
    description = re.sub(r'^\s+|\s+$', '', description)  # Trim start/end
    description = re.sub(r' +', ' ', description)  # Multiple spaces to single
    
    return description


def get_schema_details(spec: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
    """Get detailed information for a specific schema."""
    components = spec.get('components', {})
    schemas = components.get('schemas', {})
    
    if schema_name not in schemas:
        available_schemas = list(schemas.keys())
        raise ValueError(f"Schema '{schema_name}' not found in spec. Available schemas: {', '.join(available_schemas[:10])}{'...' if len(available_schemas) > 10 else ''}")
    
    schema_details = schemas[schema_name]
    
    return {
        'schema_name': schema_name,
        'definition': schema_details
    }


def get_endpoint_details(spec: Dict[str, Any], path: str, method: str) -> Dict[str, Any]:
    """Get detailed information for a specific endpoint."""
    paths = spec.get('paths', {})
    
    if path not in paths:
        raise ValueError(f"Path '{path}' not found in spec")
    
    path_info = paths[path]
    method_lower = method.lower()
    
    if method_lower not in path_info:
        available_methods = [m.upper() for m in path_info.keys() if m.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']]
        raise ValueError(f"Method '{method.upper()}' not found for path '{path}'. Available: {', '.join(available_methods)}")
    
    endpoint_details = path_info[method_lower]
    
    # Add path and method to the details
    result = {
        'path': path,
        'method': method.upper(),
        **endpoint_details
    }
    
    # Add server info for easy access
    result['servers'] = spec.get('servers', [])
    
    return result


async def execute_api_call(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Execute an HTTP API call and return the response details."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Prepare request
            request_headers = headers or {}
            
            # Handle different body types
            request_kwargs = {
                'method': method.upper(),
                'url': url,
                'headers': request_headers,
                'params': params,
            }
            
            if body is not None:
                if isinstance(body, (dict, list)):
                    request_kwargs['json'] = body
                    if 'content-type' not in {k.lower() for k in request_headers.keys()}:
                        request_headers['Content-Type'] = 'application/json'
                else:
                    request_kwargs['content'] = str(body)
            
            # Execute request
            response = await client.request(**request_kwargs)
            
            # Parse response
            try:
                response_json = response.json()
            except Exception:
                response_json = None
            
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'json': response_json,
                'text': response.text,
                'url': str(response.url),
                'request': {
                    'method': method.upper(),
                    'url': url,
                    'headers': request_headers,
                    'params': params,
                    'body': body
                }
            }
    except Exception as e:
        return {
            'error': str(e),
            'request': {
                'method': method.upper(),
                'url': url,
                'headers': headers,
                'params': params,
                'body': body
            }
        }


def create_server() -> Server:
    """Create and configure the MCP server."""
    app = Server("mcp-api-explorer")

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
        if name == "load-openapi-spec":
            file_path_or_url = arguments.get("file_path_or_url")
            spec_id = arguments.get("spec_id", "default")
            
            if not file_path_or_url:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: file_path_or_url is required",
                    )
                ]
            
            try:
                spec = load_openapi_spec(file_path_or_url)
                loaded_specs[spec_id] = spec
                summary = summarize_openapi_spec(spec)
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"OpenAPI spec loaded successfully with ID '{spec_id}':\n\n{summary}",
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error loading OpenAPI spec: {str(e)}",
                    )
                ]
        
        elif name == "get-endpoint-details":
            spec_id = arguments.get("spec_id", "default")
            path = arguments.get("path")
            method = arguments.get("method")
            
            if not path or not method:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: both path and method are required",
                    )
                ]
            
            try:
                if spec_id not in loaded_specs:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"No spec loaded with ID '{spec_id}'. Load a spec first using 'load-openapi-spec'.",
                        )
                    ]
                
                spec = loaded_specs[spec_id]
                details = get_endpoint_details(spec, path, method)
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Endpoint details:\n\n{json.dumps(details, indent=2)}",
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error getting endpoint details: {str(e)}",
                    )
                ]
        
        elif name == "get-schema-details":
            schema_name = arguments.get("schema_name")
            spec_id = arguments.get("spec_id", "default")
            
            if not schema_name:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: schema_name is required",
                    )
                ]
            
            try:
                if spec_id not in loaded_specs:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"No spec loaded with ID '{spec_id}'. Load a spec first using 'load-openapi-spec'.",
                        )
                    ]
                
                spec = loaded_specs[spec_id]
                details = get_schema_details(spec, schema_name)
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Schema details:\n\n{json.dumps(details, indent=2)}",
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error getting schema details: {str(e)}",
                    )
                ]
        
        elif name == "execute-api-call":
            url = arguments.get("url")
            method = arguments.get("method", "GET")
            headers = arguments.get("headers")
            params = arguments.get("params")
            body = arguments.get("body")
            timeout = arguments.get("timeout", 30.0)
            
            if not url:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: url is required",
                    )
                ]
            
            try:
                result = await execute_api_call(url, method, headers, params, body, timeout)
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"API call result:\n\n{json.dumps(result, indent=2)}",
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error executing API call: {str(e)}",
                    )
                ]
        
        else:
            return [
                types.TextContent(
                    type="text",
                    text=f"Unknown tool: {name}",
                )
            ]

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="load-openapi-spec",
                description=(
                    "Load an OpenAPI/Swagger specification from a file path or URL "
                    "and return a summary of available endpoints"
                ),
                inputSchema={
                    "type": "object",
                    "required": ["file_path_or_url"],
                    "properties": {
                        "file_path_or_url": {
                            "type": "string",
                            "description": "Path to OpenAPI spec file or URL to fetch it from",
                        },
                        "spec_id": {
                            "type": "string",
                            "description": "Identifier for this spec (default: 'default')",
                            "default": "default",
                        },
                    },
                },
            ),
            types.Tool(
                name="get-endpoint-details",
                description=(
                    "Get detailed information about a specific endpoint from a loaded "
                    "OpenAPI specification"
                ),
                inputSchema={
                    "type": "object",
                    "required": ["path", "method"],
                    "properties": {
                        "spec_id": {
                            "type": "string",
                            "description": "ID of the loaded spec (default: 'default')",
                            "default": "default",
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., '/users/{id}')",
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, DELETE, etc.)",
                        },
                    },
                },
            ),
            types.Tool(
                name="get-schema-details",
                description=(
                    "Get detailed information about a specific schema from a loaded "
                    "OpenAPI specification"
                ),
                inputSchema={
                    "type": "object",
                    "required": ["schema_name"],
                    "properties": {
                        "schema_name": {
                            "type": "string",
                            "description": "Name of the schema to get details for",
                        },
                        "spec_id": {
                            "type": "string",
                            "description": "ID of the loaded spec (default: 'default')",
                            "default": "default",
                        },
                    },
                },
            ),
            types.Tool(
                name="execute-api-call",
                description=(
                    "Execute an HTTP API call with specified parameters"
                ),
                inputSchema={
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Full URL for the API call",
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method (default: GET)",
                            "default": "GET",
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers as key-value pairs",
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters as key-value pairs",
                        },
                        "body": {
                            "description": "Request body (will be JSON-encoded if object/array)",
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Request timeout in seconds (default: 30)",
                            "default": 30.0,
                        },
                    },
                },
            ),
        ]

    return app


@click.group()
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
def cli(log_level: str):
    """API Explorer - OpenAPI spec explorer with MCP server modes."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@cli.command()
@click.option("--port", default=3000, help="Port to listen on for HTTP")
@click.option(
    "--json-response",
    is_flag=True,
    default=False,
    help="Enable JSON responses instead of SSE streams",
)
def server(
    port: int,
    json_response: bool,
) -> int:
    """Run as MCP server with HTTP transport."""
    app = create_server()

    # Create the session manager with true stateless mode
    session_manager = StreamableHTTPSessionManager(
        app=app,
        event_store=None,
        json_response=json_response,
        stateless=True,
    )

    async def handle_streamable_http(
        scope: Scope, receive: Receive, send: Send
    ) -> None:
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for session manager."""
        async with session_manager.run():
            logger.info("Application started with StreamableHTTP session manager!")
            try:
                yield
            finally:
                logger.info("Application shutting down...")

    # Create an ASGI application using the transport
    starlette_app = Starlette(
        debug=True,
        routes=[
            Mount("/mcp", app=handle_streamable_http),
        ],
        lifespan=lifespan,
    )

    import uvicorn

    uvicorn.run(starlette_app, host="127.0.0.1", port=port)

    return 0


@cli.command()
def stdio() -> int:
    """Run as MCP server with stdio transport."""
    app = create_server()
    
    async def run_stdio():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    
    anyio.run(run_stdio)
    return 0


def main() -> int:
    """Main entry point."""
    try:
        cli()
        return 0
    except SystemExit as e:
        if e.code is None:
            return 0
        elif isinstance(e.code, int):
            return e.code
        else:
            return 1
    except Exception:
        return 1