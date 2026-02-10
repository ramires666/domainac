from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.domain_checker import DomainCheckResult, check_domain_registration

app = FastAPI(
    title="Domain Checker API",
    version="1.1.0",
    description="Domain registration checker (RDAP first, WHOIS fallback).",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


class DomainCheckResponse(BaseModel):
    domain: str
    registered: bool | None
    status: str
    error: str | None = None


class BatchCheckRequest(BaseModel):
    domains: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="List of domains to check",
    )


class BatchCheckResponse(BaseModel):
    results: list[DomainCheckResponse]


def _check_to_response(domain: str) -> DomainCheckResponse:
    try:
        result: DomainCheckResult = check_domain_registration(domain)
    except ValueError as exc:
        sanitized = domain.strip().lower()
        return DomainCheckResponse(
            domain=sanitized or domain,
            registered=None,
            status="invalid",
            error=str(exc),
        )

    return DomainCheckResponse(
        domain=result.domain,
        registered=result.registered,
        status=result.status,
        error=result.error,
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/swagger")


@app.get("/swagger", include_in_schema=False)
def swagger_alias() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - Swagger UI",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/check", response_model=DomainCheckResponse)
def check_domain(
    domain: str = Query(..., description="Domain name to check, e.g. example.com"),
) -> DomainCheckResponse:
    response = _check_to_response(domain)
    if response.status == "invalid":
        raise HTTPException(status_code=400, detail=response.error or "Invalid domain")
    return response


@app.post("/check/batch", response_model=BatchCheckResponse)
def check_domains_batch(payload: BatchCheckRequest) -> BatchCheckResponse:
    results = [_check_to_response(domain) for domain in payload.domains]
    return BatchCheckResponse(results=results)
