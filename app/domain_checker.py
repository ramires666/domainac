from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import whois
from whois.parser import PywhoisError

DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9-]{1,63}$")
IANA_RDAP_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
RDAP_TIMEOUT_SECONDS = 5
NO_MATCH_PATTERNS = (
    "no match for",
    "not found",
    "no data found",
    "status: free",
    "domain you requested is not known",
    "is available",
    "object does not exist",
)


@dataclass
class DomainCheckResult:
    domain: str
    registered: bool | None
    status: str
    error: str | None = None


def _extract_domain(value: str) -> str:
    raw = value.strip().rstrip(".").lower()
    if not raw:
        raise ValueError("Domain is empty")

    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    candidate = parsed.hostname or raw
    if not candidate:
        raise ValueError("Invalid domain")

    try:
        ascii_domain = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Invalid domain") from exc

    labels = ascii_domain.split(".")
    if len(labels) < 2:
        raise ValueError("Domain must contain a TLD")

    for label in labels:
        if not DOMAIN_LABEL_RE.match(label):
            raise ValueError("Invalid domain")
        if label.startswith("-") or label.endswith("-"):
            raise ValueError("Invalid domain")

    if len(ascii_domain) > 253:
        raise ValueError("Invalid domain")

    return ascii_domain


def _looks_unregistered(payload: Any) -> bool:
    raw = getattr(payload, "text", None)
    if isinstance(raw, list):
        text = "\n".join(part for part in raw if isinstance(part, str)).lower()
    elif isinstance(raw, str):
        text = raw.lower()
    else:
        text = str(payload).lower()

    return any(pattern in text for pattern in NO_MATCH_PATTERNS)


@lru_cache(maxsize=1)
def _rdap_bootstrap() -> dict[str, list[str]]:
    request = Request(
        IANA_RDAP_BOOTSTRAP_URL,
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=RDAP_TIMEOUT_SECONDS) as response:  # noqa: S310
        data = json.load(response)

    mapping: dict[str, list[str]] = {}
    for service in data.get("services", []):
        if not isinstance(service, list) or len(service) != 2:
            continue

        tlds, urls = service
        if not isinstance(tlds, list) or not isinstance(urls, list):
            continue

        normalized_urls = [url for url in urls if isinstance(url, str) and url]
        if not normalized_urls:
            continue

        for tld in tlds:
            if isinstance(tld, str):
                mapping[tld.lower()] = normalized_urls

    return mapping


def _check_with_rdap(domain: str) -> DomainCheckResult:
    tld = domain.rsplit(".", 1)[-1]

    try:
        bootstrap = _rdap_bootstrap()
    except Exception as exc:  # noqa: BLE001
        return DomainCheckResult(
            domain=domain,
            registered=None,
            status="unknown",
            error=f"RDAP bootstrap failed: {exc}",
        )

    urls = bootstrap.get(tld)
    if not urls:
        return DomainCheckResult(
            domain=domain,
            registered=None,
            status="unknown",
            error=f"RDAP server is not available for .{tld}",
        )

    last_error: str | None = None
    for base_url in urls:
        endpoint = f"{base_url.rstrip('/')}/domain/{quote(domain)}"
        request = Request(
            endpoint,
            headers={"Accept": "application/rdap+json, application/json"},
        )

        try:
            with urlopen(request, timeout=RDAP_TIMEOUT_SECONDS) as response:  # noqa: S310
                status_code = getattr(response, "status", 200)
                payload = json.load(response)
        except HTTPError as exc:
            if exc.code == 404:
                return DomainCheckResult(
                    domain=domain,
                    registered=False,
                    status="unregistered",
                )
            last_error = f"RDAP HTTP {exc.code} from {base_url}"
            continue
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = f"RDAP query failed for {base_url}: {exc}"
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = f"RDAP query failed for {base_url}: {exc}"
            continue

        if status_code == 404:
            return DomainCheckResult(
                domain=domain,
                registered=False,
                status="unregistered",
            )

        if status_code != 200:
            last_error = f"RDAP returned unexpected status {status_code} from {base_url}"
            continue

        object_class = str(payload.get("objectClassName", "")).lower()
        ldh_name = str(payload.get("ldhName", "")).lower()
        handle = payload.get("handle")
        title = str(payload.get("title", "")).lower()
        description_value = payload.get("description", "")
        if isinstance(description_value, list):
            description = " ".join(str(item).lower() for item in description_value)
        else:
            description = str(description_value).lower()

        if "not found" in title or "not found" in description:
            return DomainCheckResult(
                domain=domain,
                registered=False,
                status="unregistered",
            )

        if object_class == "domain" or ldh_name == domain or bool(handle):
            return DomainCheckResult(
                domain=domain,
                registered=True,
                status="registered",
            )

        last_error = f"RDAP response was inconclusive from {base_url}"

    return DomainCheckResult(
        domain=domain,
        registered=None,
        status="unknown",
        error=last_error or "RDAP lookup failed",
    )


def _check_with_whois(domain: str) -> DomainCheckResult:
    try:
        data = whois.whois(domain)
    except PywhoisError:
        return DomainCheckResult(
            domain=domain,
            registered=False,
            status="unregistered",
        )
    except Exception as exc:  # noqa: BLE001
        return DomainCheckResult(
            domain=domain,
            registered=None,
            status="unknown",
            error=f"WHOIS query failed: {exc}",
        )

    domain_name = getattr(data, "domain_name", None)
    if isinstance(domain_name, list):
        registered = any(bool(item) for item in domain_name)
    else:
        registered = bool(domain_name)

    if registered:
        return DomainCheckResult(
            domain=domain,
            registered=True,
            status="registered",
        )

    if _looks_unregistered(data):
        return DomainCheckResult(
            domain=domain,
            registered=False,
            status="unregistered",
        )

    return DomainCheckResult(
        domain=domain,
        registered=None,
        status="unknown",
        error="WHOIS response was inconclusive",
    )


def check_domain_registration(domain: str) -> DomainCheckResult:
    normalized = _extract_domain(domain)
    rdap_result = _check_with_rdap(normalized)
    if rdap_result.registered is not None:
        return rdap_result

    whois_result = _check_with_whois(normalized)
    if whois_result.registered is not None:
        return whois_result

    errors = []
    if rdap_result.error:
        errors.append(f"RDAP: {rdap_result.error}")
    if whois_result.error:
        errors.append(f"WHOIS: {whois_result.error}")

    return DomainCheckResult(
        domain=normalized,
        registered=None,
        status="unknown",
        error="; ".join(errors) if errors else "Domain lookup failed",
    )
