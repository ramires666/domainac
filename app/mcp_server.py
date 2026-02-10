from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

try:
    from app.domain_checker import DomainCheckResult, check_domain_registration
except ModuleNotFoundError:  # pragma: no cover
    from domain_checker import DomainCheckResult, check_domain_registration

DEFAULT_STREAMABLE_HTTP_PATH = "/mcp"


def _result_to_payload(result: DomainCheckResult) -> dict[str, Any]:
    return {
        "domain": result.domain,
        "registered": result.registered,
        "status": result.status,
        "error": result.error,
    }


def _check_to_payload(domain: str) -> dict[str, Any]:
    try:
        result = check_domain_registration(domain)
    except ValueError as exc:
        sanitized = domain.strip().lower()
        return {
            "domain": sanitized or domain,
            "registered": None,
            "status": "invalid",
            "error": str(exc),
        }

    return _result_to_payload(result)


def create_mcp_server(
    host: str = "127.0.0.1",
    port: int = 18081,
    streamable_http_path: str = DEFAULT_STREAMABLE_HTTP_PATH,
) -> FastMCP:
    server = FastMCP(
        name="domainac-mcp",
        instructions="Check whether domains are registered (RDAP first, WHOIS fallback).",
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
    )

    @server.tool(
        name="check_domain",
        description="Check one domain. Returns domain, registered, status, and error.",
        structured_output=True,
    )
    def check_domain_tool(domain: str) -> dict[str, Any]:
        return _check_to_payload(domain)

    @server.tool(
        name="check_domains_batch",
        description=(
            "Check multiple domains at once. "
            "Accepts 1..200 domains and returns {results:[...]}."
        ),
        structured_output=True,
    )
    def check_domains_batch_tool(domains: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not domains:
            raise ValueError("`domains` must contain at least one value")
        if len(domains) > 200:
            raise ValueError("`domains` supports up to 200 values")
        return {"results": [_check_to_payload(domain) for domain in domains]}

    return server
