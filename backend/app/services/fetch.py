"""SSRF-safe URL retrieval and HTML text extraction."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import get_settings
from ..errors import SSRFBlocked

settings = get_settings()

BLOCKED_PORTS = {0, 22, 23, 25, 53, 110, 143, 445, 1433, 1521, 3306, 5432, 6379, 11211, 27017}
ALLOWED_SCHEMES = {"http", "https"}


@dataclass
class FetchedPage:
    url: str
    final_url: str
    status: int
    title: str
    description: str
    text: str
    links: list[str] = field(default_factory=list)
    content_type: str = ""
    bytes_read: int = 0


def _is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def validate_url(url: str, *, allow_private: bool | None = None) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise SSRFBlocked("Only http and https URLs are allowed")
    if not parsed.hostname:
        raise SSRFBlocked("URL must include a hostname")
    if parsed.username or parsed.password:
        raise SSRFBlocked("URLs with embedded credentials are not allowed")
    if parsed.port and parsed.port in BLOCKED_PORTS:
        raise SSRFBlocked("Destination port is not allowed")
    permit_private = settings.allow_private_urls if allow_private is None else allow_private
    host = parsed.hostname
    if host.lower() in {"localhost", "localhost.localdomain"} and not permit_private:
        raise SSRFBlocked("Localhost destinations are blocked")
    try:
        infos = await asyncio.get_running_loop().run_in_executor(None, socket.getaddrinfo, host, None)
    except socket.gaierror as exc:
        raise SSRFBlocked(f"Host could not be resolved: {host}") from exc
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if _is_forbidden_ip(ip) and not permit_private:
            raise SSRFBlocked(f"Private or reserved address blocked: {address}")
    return parsed.geturl()


def extract_html(html: str, base_url: str) -> tuple[str, str, str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    description = ""
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta and meta.get("content"):
        description = str(meta["content"]).strip()
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = "\n".join(lines)
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(base_url, anchor["href"])
        if absolute.startswith(("http://", "https://")) and absolute not in links:
            links.append(absolute)
        if len(links) >= 50:
            break
    return title, description, cleaned[:120_000], links


async def fetch_page(url: str, *, allow_private: bool | None = None) -> FetchedPage:
    current = await validate_url(url, allow_private=allow_private)
    async with httpx.AsyncClient(
        timeout=settings.url_fetch_timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": "NexaMindAI/1.0 (+https://nexamind.local)"},
    ) as client:
        for _ in range(4):
            response = await client.get(current)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    break
                current = await validate_url(urljoin(current, location), allow_private=allow_private)
                continue
            break
        if response.status_code >= 400:
            return FetchedPage(
                url=url,
                final_url=str(response.url),
                status=response.status_code,
                title="",
                description="",
                text="",
                content_type=response.headers.get("content-type", ""),
                bytes_read=0,
            )
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type and "application/xhtml" not in content_type:
            raise ValueError(f"Unsupported content type: {content_type or 'unknown'}")
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > settings.max_url_bytes:
                raise ValueError("Response exceeded the size limit")
            chunks.append(chunk)
        body = b"".join(chunks)
        html = body.decode(response.encoding or "utf-8", "replace")
        if "text/html" in content_type or "xhtml" in content_type:
            title, description, text, links = extract_html(html, str(response.url))
        else:
            title, description, links = "Plain text document", "", []
            text = html
        return FetchedPage(
            url=url,
            final_url=str(response.url),
            status=response.status_code,
            title=title,
            description=description,
            text=text,
            links=links,
            content_type=content_type,
            bytes_read=len(body),
        )
