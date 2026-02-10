# domainac

A simple FastAPI service to check whether a domain is registered.
Lookup flow: `RDAP` first, then fallback to `WHOIS`.

## Run With Docker

```bash
docker compose up --build
```

The API will be available at `http://localhost:18080`.

The service uses a non-standard 5-digit port `18080` and always checks if the port is free before starting.
If the port is already in use, startup fails with an error.

## API Documentation

- Swagger UI: `http://localhost:18080/swagger`
- Swagger UI (default FastAPI URL): `http://localhost:18080/docs`
- ReDoc: `http://localhost:18080/redoc`
- OpenAPI JSON: `http://localhost:18080/openapi.json`

## Run Without Docker

```bash
python3 -m pip install -r requirements.txt
python3 -m app.run_server
```

By default, `PORT=18080` is used. You can override it:

```bash
PORT=19090 python3 -m app.run_server
```

## Example Requests

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

## Response Format

```json
{
  "domain": "example.com",
  "registered": true,
  "status": "registered",
  "error": null
}
```

`status` can be:
- `registered`
- `unregistered`
- `unknown` (if WHOIS returned an inconclusive response)
- `invalid` (batch check only, when a domain is invalid)
