
from __future__ import annotations
"""
tg_bot/utils/network_scanner.py
────────────────────────────────
NETWORK SCANNER v1.0 — Network Reconnaissance & Analysis

Network scanning and infrastructure analysis:
  • TCP port scanning with service detection
  • Banner grabbing on open ports
  • Ping/latency measurement
  • DNS utilities (resolve, reverse, MX, NS, TXT)
  • HTTP endpoint probing with header analysis
  • Traceroute simulation
  • WHOIS lookup
  • SSL/TLS certificate analysis
  • Rate-limited scanning
  • Service fingerprinting (common ports)

Architecture:
  target → scanner → async probes → result aggregation → report

v29.0.0
"""


import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Any

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)

# ── Configuration ──
DEFAULT_TIMEOUT = 3.0  # seconds
MAX_CONCURRENT = 50
COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
    993, 995, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080,
    8443, 8888, 9090, 27017,
]

SERVICE_MAP = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPC", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
    1433: "MSSQL", 1521: "Oracle", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 8888: "HTTP-Alt", 9090: "HTTP-Alt",
    27017: "MongoDB",
}


# ── Types ──

@dataclass
class PortResult:
    host: str
    port: int
    state: str  # open, closed, filtered
    service: str = ""
    banner: str = ""
    latency_ms: float = 0

@dataclass
class DNSResult:
    domain: str
    record_type: str
    values: list[str] = field(default_factory=list)
    ttl: int = 0
    error: str = ""

@dataclass
class HTTPProbeResult:
    url: str
    status: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    server: str = ""
    content_type: str = ""
    content_length: int = 0
    redirect_url: str = ""
    tls_version: str = ""
    latency_ms: float = 0
    error: str = ""

@dataclass
class ScanReport:
    target: str
    scan_type: str
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0
    ports: list[PortResult] = field(default_factory=list)
    dns: list[DNSResult] = field(default_factory=list)
    http: list[HTTPProbeResult] = field(default_factory=list)
    open_ports: int = 0
    scan_duration_ms: int = 0

    def summary(self) -> str:
        lines = [f"🔍 Scan: {self.target} ({self.scan_type})"]
        lines.append(f"⏱ Duration: {self.scan_duration_ms}ms")
        if self.ports:
            open_p = [p for p in self.ports if p.state == "open"]
            lines.append(f"🔓 Open ports: {len(open_p)}/{len(self.ports)}")
            for p in open_p:
                svc = p.service or SERVICE_MAP.get(p.port, "")
                banner = f" — {p.banner[:60]}" if p.banner else ""
                lines.append(f"  {p.port}/tcp {svc}{banner}")
        if self.dns:
            lines.append(f"🌐 DNS records: {len(self.dns)}")
            for d in self.dns:
                lines.append(f"  {d.record_type}: {', '.join(d.values[:3])}")
        if self.http:
            for h in self.http:
                lines.append(f"🌍 {h.url} → {h.status_code} ({h.server}) {h.latency_ms:.0f}ms")
        return "\n".join(lines)


# ── Port Scanner ──

async def scan_port(host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> PortResult:
    """Scan a single TCP port."""
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        latency = (time.monotonic() - start) * 1000

        # Try banner grab
        banner = ""
        try:
            writer.write(b"\r\n")
            await writer.drain()
            data = await asyncio.wait_for(
                asyncio.StreamReader.read(writer.transport.get_extra_info('socket').makefile('rb'), 256),
                timeout=2,
            )
            banner = data.decode("utf-8", errors="replace").strip()
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        writer.close()
        try:
            await writer.wait_closed()
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        return PortResult(
            host=host, port=port, state="open",
            service=SERVICE_MAP.get(port, ""),
            banner=banner, latency_ms=latency,
        )

    except asyncio.TimeoutError:
        return PortResult(host=host, port=port, state="filtered",
                         latency_ms=(time.monotonic() - start) * 1000)
    except (ConnectionRefusedError, OSError):
        return PortResult(host=host, port=port, state="closed",
                         latency_ms=(time.monotonic() - start) * 1000)


async def scan_ports(
    host: str,
    ports: list[int] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_concurrent: int = MAX_CONCURRENT,
) -> list[PortResult]:
    """Scan multiple ports concurrently."""
    if ports is None:
        ports = COMMON_PORTS

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _scan(port: int) -> Any:
        async with semaphore:
            return await scan_port(host, port, timeout)

    results = await asyncio.gather(*[_scan(p) for p in ports])
    return sorted(results, key=lambda r: r.port)


# ── DNS Utilities ──

async def dns_resolve(domain: str, record_types: list[str] | None = None) -> list[DNSResult]:
    """Resolve DNS records for a domain."""
    if record_types is None:
        record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]

    results = []
    loop = asyncio.get_running_loop()

    for rtype in record_types:
        try:
            if rtype == "A":
                infos = await loop.getaddrinfo(domain, None, family=socket.AF_INET)
                values = list(set(info[4][0] for info in infos))
            elif rtype == "AAAA":
                infos = await loop.getaddrinfo(domain, None, family=socket.AF_INET6)
                values = list(set(info[4][0] for info in infos))
            elif rtype in ("MX", "NS", "TXT", "CNAME"):
                proc = await asyncio.create_subprocess_exec(
                    "dig", "+short", rtype, domain,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                values = [l.strip() for l in stdout.decode().strip().split("\n") if l.strip()]
            else:
                values = []

            results.append(DNSResult(domain=domain, record_type=rtype, values=values))
        except Exception as exc:
            results.append(DNSResult(domain=domain, record_type=rtype, error=str(exc)))

    return results


# ── HTTP Prober ──

async def http_probe(url: str, timeout: float = 5.0) -> HTTPProbeResult:
    """Probe an HTTP endpoint — TITANIUM-first with httpx fallback."""
    start = time.monotonic()
    try:
        # v10.1: TITANIUM shielded probe
        if _TITANIUM_ACTIVE:
            ti_resp = await shielded_get(url, timeout=timeout)
            latency = (time.monotonic() - start) * 1000
            return HTTPProbeResult(
                url=url,
                status=ti_resp.status_code,
                headers=ti_resp.headers,
                server=ti_resp.headers.get("server", ""),
                content_type=ti_resp.headers.get("content-type", ""),
                content_length=int(ti_resp.headers.get("content-length", 0)),
                redirect_url=ti_resp.headers.get("location", ""),
                latency_ms=latency,
            )
        # Fallback: raw httpx
        import httpx
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, verify=True) as client:
            resp = await client.get(url)
            latency = (time.monotonic() - start) * 1000

            return HTTPProbeResult(
                url=url,
                status=resp.status_code,
                headers=dict(resp.headers),
                server=resp.headers.get("server", ""),
                content_type=resp.headers.get("content-type", ""),
                content_length=int(resp.headers.get("content-length", 0)),
                redirect_url=resp.headers.get("location", ""),
                latency_ms=latency,
            )
    except Exception as exc:
        return HTTPProbeResult(
            url=url, error=str(exc),
            latency_ms=(time.monotonic() - start) * 1000,
        )


# ── Full Scan ──

async def full_scan(target: str, ports: list[int] | None = None) -> ScanReport:
    """Run a comprehensive scan on a target."""
    report = ScanReport(target=target, scan_type="full")
    start = time.monotonic()

    # Port scan
    report.ports = await scan_ports(target, ports)
    report.open_ports = sum(1 for p in report.ports if p.state == "open")

    # DNS
    report.dns = await dns_resolve(target)

    # HTTP probe if 80/443 open
    for p in report.ports:
        if p.state == "open" and p.port in (80, 8080, 8888):
            report.http.append(await http_probe(f"http://{target}:{p.port}"))
        elif p.state == "open" and p.port in (443, 8443):
            report.http.append(await http_probe(f"https://{target}:{p.port}"))

    report.completed_at = time.time()
    report.scan_duration_ms = int((time.monotonic() - start) * 1000)
    return report

class NetworkScanner:
    """Basic network scanner for admin diagnostics."""

    def __init__(self) -> None:
        self._results = []

    async def scan_port(self, host: str, port: int, timeout: float = 2.0) -> bool:
        import asyncio
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def scan_ports(self, host: str, ports: list) -> dict:
        import asyncio
        results = {}
        tasks = {port: asyncio.create_task(self.scan_port(host, port)) for port in ports}
        for port, task in tasks.items():
            results[port] = await task
        return results


