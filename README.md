# domainac

Domain registration checker with two interfaces:
- HTTP API (`FastAPI`)
- MCP server (`Model Context Protocol`)

Lookup flow is the same for both: `RDAP` first, then `WHOIS` fallback.

## Run With Docker

```bash
docker compose up --build
```

After startup:
- HTTP API: `http://localhost:18080`
- MCP (Streamable HTTP): `http://localhost:18081/mcp`

Both services use non-standard 5-digit ports and check port availability before starting.

## Run Without Docker

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run HTTP API:

```bash
python3 -m app.run_server
```

Run MCP server (default transport is `stdio`):

```bash
python3 -m app.run_mcp_server
```

Run MCP server over HTTP (`streamable-http`):

```bash
MCP_TRANSPORT=streamable-http MCP_PORT=18081 python3 -m app.run_mcp_server
```

Example MCP client config (`stdio` transport):

```json
{
  "mcpServers": {
    "domainac": {
      "command": "python3",
      "args": ["-m", "app.run_mcp_server"]
    }
  }
}
```

Example MCP client config (`streamable-http` transport):

```json
{
  "mcpServers": {
    "domainac": {
      "url": "http://localhost:18081/mcp"
    }
  }
}
```

## HTTP API Documentation

- Swagger UI: `http://localhost:18080/swagger`
- Swagger UI (default FastAPI URL): `http://localhost:18080/docs`
- ReDoc: `http://localhost:18080/redoc`
- OpenAPI JSON: `http://localhost:18080/openapi.json`

## HTTP API Examples

Single domain check:

```bash
curl "http://localhost:18080/check?domain=example.com"
```

Batch domain check:

```bash
curl -X POST "http://localhost:18080/check/batch" \
  -H "Content-Type: application/json" \
  -d '{"domains":["example.com","google.com","bad domain"]}'
```

Health-check:

```bash
curl "http://localhost:18080/health"
```

## MCP Tools

- `check_domain(domain: str)`
- `check_domains_batch(domains: list[str])`

Tool result format:

```json
{
  "domain": "example.com",
  "registered": true,
  "status": "registered",
  "error": null
}
```

`status` values:
- `registered`
- `unregistered`
- `unknown` (lookup was inconclusive)
- `invalid` (invalid domain input)
