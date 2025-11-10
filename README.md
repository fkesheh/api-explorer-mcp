# API Explorer MCP Server

A Model Context Protocol (MCP) server that provides efficient OpenAPI/Swagger specification exploration and API testing capabilities. Instead of loading entire API specs into context (which consumes many tokens), this server provides a summary-first approach with detailed endpoint exploration.

## Transport Modes

### 🌐 **Server Mode** - HTTP Transport
Perfect for web-based integrations and deployments:
- HTTP-based MCP server on configurable port
- Streamable HTTP sessions with SSE or JSON responses
- Easy to test with curl and web tools
- Stateful spec management in memory

### 📡 **Stdio Mode** - Standard Input/Output Transport  
Ideal for local MCP client integration:
- Standard input/output transport for MCP clients
- Direct integration with AI assistants and automation tools
- Efficient binary protocol communication
- Perfect for local MCP deployments

## Features

- **Smart OpenAPI Loading**: Load OpenAPI/Swagger specs from files or URLs with token-efficient summaries
- **Complete Schema Details**: Get detailed information about any schema/model definition
- **Endpoint Discovery**: Get high-level overviews of all available endpoints
- **Detailed Endpoint Info**: Retrieve comprehensive details for specific endpoints
- **API Execution**: Execute HTTP requests with full parameter support
- **Multiple Spec Support**: Manage multiple API specifications simultaneously
- **Dual Transport**: HTTP server for web deployment + stdio for local deployment

## 🚀 Quickstart

Get up and running in 2 minutes:

### 1. Add to Your MCP Client Configuration

Add this to your MCP configuration file (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "api-explorer": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "api-explorer-mcp",
        "api-explorer-mcp",
        "stdio"
      ]
    }
  }
}
```

### 2. Start Using It

Once configured, you can immediately start exploring APIs with natural language:

```
Load the Shippo API spec from https://docs.goshippo.com/spec/shippoapi/public-api.yaml
```

```
Show me the Address schema details
```

```
Get shipping rates from San Francisco to New York for a 1lb package
```

### 3. What You Get

- ✅ **Zero Installation** - Dependencies managed automatically
- ✅ **Token Efficient** - Smart summaries instead of full spec dumps  
- ✅ **Real API Testing** - Execute actual HTTP requests
- ✅ **Multiple APIs** - Load and switch between different specifications

### Need More Control?

- **Web Deployment**: Use [Server Mode](#-server-mode---http-transport) for HTTP-based integrations
- **Detailed Setup**: See [Installation & Setup](#installation--setup) for advanced configuration
- **API Reference**: Check [MCP Tools Available](#mcp-tools-available) for all capabilities

## Installation & Setup

### Dependencies
This project uses `uv` for dependency management. No local installation required - dependencies are managed automatically via `uv run --with`.

### Required Dependencies
- `anyio>=4.5`
- `click>=8.1.0`
- `httpx>=0.27`
- `mcp`
- `PyYAML>=6.0`
- `starlette`
- `uvicorn`

## Usage

### Running the Server

#### HTTP Transport (Server Mode)
```bash
# Start HTTP MCP server (default port 3000)
uv run --with "anyio>=4.5,click>=8.1.0,httpx>=0.27,mcp,PyYAML>=6.0,starlette,uvicorn" main.py server

# Custom port and debug logging
uv run --with "anyio>=4.5,click>=8.1.0,httpx>=0.27,mcp,PyYAML>=6.0,starlette,uvicorn" main.py server --port 8080 --log-level DEBUG

# JSON responses instead of SSE streams
uv run --with "anyio>=4.5,click>=8.1.0,httpx>=0.27,mcp,PyYAML>=6.0,starlette,uvicorn" main.py server --json-response
```

#### Stdio Transport (Stdio Mode)
```bash
# Start stdio MCP server
uv run --with "anyio>=4.5,click>=8.1.0,httpx>=0.27,mcp,PyYAML>=6.0,starlette,uvicorn" main.py stdio

# With debug logging
uv run --with "anyio>=4.5,click>=8.1.0,httpx>=0.27,mcp,PyYAML>=6.0,starlette,uvicorn" main.py --log-level DEBUG stdio
```

## MCP Client Integration

### Cursor/Claude Desktop Configuration

Add this to your MCP configuration file (e.g., `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "api-explorer": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "anyio>=4.5,click>=8.1.0,httpx>=0.27,mcp,PyYAML>=6.0,starlette,uvicorn",
        "/path/to/your/api-explorer-mcp/main.py",
        "stdio"
      ]
    }
  }
}
```

**Replace `/path/to/your/api-explorer-mcp/` with the actual path to this project directory.**

### Benefits of this Setup
- ✅ **No Installation Required**: Dependencies managed automatically by `uv`
- ✅ **Isolated Environment**: Each run gets fresh, isolated dependencies
- ✅ **Version Pinning**: Specific dependency versions ensure consistency
- ✅ **Zero Maintenance**: No virtual environments or dependency conflicts
- ✅ **Cross-Platform**: Works on any system with `uv` installed

## MCP Tools Available

### 1. `load-openapi-spec`
Load an OpenAPI/Swagger specification and get a concise summary.

**Parameters:**
- `file_path_or_url` (required): Path to local file or URL to fetch the spec
- `spec_id` (optional): Identifier for this spec (default: "default")

**Example:**
```json
{
  "file_path_or_url": "https://petstore3.swagger.io/api/v3/openapi.json",
  "spec_id": "petstore"
}
```

### 2. `get-schema-details`
Get detailed information about a specific schema from a loaded specification.

**Parameters:**
- `schema_name` (required): Name of the schema to get details for
- `spec_id` (optional): ID of the loaded spec (default: "default")

**Example:**
```json
{
  "schema_name": "Pet",
  "spec_id": "petstore"
}
```

### 3. `get-endpoint-details`
Get detailed information about a specific endpoint from a loaded specification.

**Parameters:**
- `path` (required): API endpoint path (e.g., `/users/{id}`)
- `method` (required): HTTP method (GET, POST, PUT, DELETE, etc.)
- `spec_id` (optional): ID of the loaded spec (default: "default")

**Example:**
```json
{
  "path": "/pet/{petId}",
  "method": "GET",
  "spec_id": "petstore"
}
```

### 4. `execute-api-call`
Execute an HTTP API call with specified parameters.

**Parameters:**
- `url` (required): Full URL for the API call
- `method` (optional): HTTP method (default: "GET")
- `headers` (optional): HTTP headers as key-value pairs
- `params` (optional): Query parameters as key-value pairs
- `body` (optional): Request body (automatically JSON-encoded if object/array)
- `timeout` (optional): Request timeout in seconds (default: 30)

**Example:**
```json
{
  "url": "https://petstore3.swagger.io/api/v3/pet/1",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer your-token",
    "Accept": "application/json"
  }
}
```

## Usage Workflow

1. **Load a Specification**: Use `load-openapi-spec` to load your API spec and see a summary of all schemas and endpoints
2. **Explore Schemas**: Use `get-schema-details` to understand data models and their properties
3. **Explore Endpoints**: Use `get-endpoint-details` to get full information about specific endpoints
4. **Execute Calls**: Use `execute-api-call` to make actual HTTP requests to the API

## Command Line Options

### Global Options
- `--log-level` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--help` - Show help message

### Server Mode Options
- `--port` - Port to listen on (default: 3000)
- `--json-response` - Enable JSON responses instead of SSE streams

## Examples

### HTTP Server Mode Testing
```bash
# 1. Start the server
uv run --with "anyio>=4.5,click>=8.1.0,httpx>=0.27,mcp,PyYAML>=6.0,starlette,uvicorn" main.py server --port 3000

# 2. Load a spec (using curl)
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "load-openapi-spec",
      "arguments": {
        "file_path_or_url": "https://petstore3.swagger.io/api/v3/openapi.json"
      }
    }
  }'

# 3. Get schema details
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "get-schema-details",
      "arguments": {
        "schema_name": "Pet"
      }
    }
  }'

# 4. Execute API call
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "execute-api-call",
      "arguments": {
        "url": "https://petstore3.swagger.io/api/v3/pet/1",
        "method": "GET"
      }
    }
  }'
```

### MCP Integration Example
Once configured in your MCP client, you can use natural language:

```
# Load Shippo API
"Load the Shippo API spec from https://docs.goshippo.com/spec/shippoapi/public-api.yaml"

# Explore schemas
"Show me the Address schema details"

# Make API calls  
"Validate this address: 215 Clayton St, San Francisco, CA 94117"
```

## Real-World Example: Shippo API

Here's a complete example using the Shippo shipping API:

### 1. Load the API Specification
```json
{
  "method": "tools/call",
  "params": {
    "name": "load-openapi-spec",
    "arguments": {
      "file_path_or_url": "https://docs.goshippo.com/spec/shippoapi/public-api.yaml",
      "spec_id": "shippo"
    }
  }
}
```

### 2. Explore Address Schema
```json
{
  "method": "tools/call", 
  "params": {
    "name": "get-schema-details",
    "arguments": {
      "schema_name": "Address",
      "spec_id": "shippo"
    }
  }
}
```

### 3. Get Address Validation Endpoint Details
```json
{
  "method": "tools/call",
  "params": {
    "name": "get-endpoint-details", 
    "arguments": {
      "path": "/addresses/{AddressId}/validate",
      "method": "GET",
      "spec_id": "shippo"
    }
  }
}
```

### 4. Validate an Address
```json
{
  "method": "tools/call",
  "params": {
    "name": "execute-api-call",
    "arguments": {
      "url": "https://api.goshippo.com/addresses",
      "method": "POST",
      "headers": {
        "Authorization": "ShippoToken shippo_test_5f7270ee3a59ac0bb0e5e993484fd472965d98c7",
        "Content-Type": "application/json"
      },
      "body": {
        "name": "Shawn Ippotle",
        "street1": "215 Clayton St",
        "city": "San Francisco", 
        "state": "CA",
        "zip": "94117",
        "country": "US",
        "validate": true
      }
    }
  }
}
```

## Benefits

### Server Mode Benefits
- ✅ **Easy Testing**: HTTP interface allows testing with curl and web tools
- ✅ **Flexible Integration**: Works with any HTTP client
- ✅ **Visual Inspection**: Easy to inspect requests and responses
- ✅ **Web Deployment**: Great for web-based integrations and services

### Stdio Mode Benefits  
- ✅ **Direct Integration**: Native MCP client communication
- ✅ **Efficient Protocol**: Binary MCP protocol for optimal performance
- ✅ **Local Ready**: Designed for local AI assistant integration
- ✅ **Standard Compliant**: Full MCP specification compliance

### Shared Benefits
- ✅ **Token Efficient**: Only load what you need, when you need it
- ✅ **Persistent State**: Loaded specs stay in memory across requests
- ✅ **Complete Coverage**: Full schema details, endpoint info, and API execution
- ✅ **Real Testing**: Actually execute API calls, not just explore documentation
- ✅ **Multiple APIs**: Handle multiple API specifications simultaneously
- ✅ **Format Support**: OpenAPI 3.x and Swagger 2.x (JSON/YAML)
- ✅ **Zero Installation**: Dependencies managed automatically by `uv`
- ✅ **Isolated Environment**: Each run gets fresh dependencies

## Supported Formats

- OpenAPI 3.x (JSON and YAML)
- Swagger 2.x (JSON and YAML)
- Auto-detection based on file extension and content

## Requirements

- [`uv`](https://docs.astral.sh/uv/) - Fast Python package installer and resolver
- Python 3.8+ (managed automatically by `uv`)

---

**Choose Your Transport:**
- Use **Server mode** for web deployment and HTTP-based integrations
- Use **Stdio mode** for local MCP client integration and AI assistants

**Zero Setup Required:** Just configure the MCP client with the `uv run` command and start exploring APIs!

