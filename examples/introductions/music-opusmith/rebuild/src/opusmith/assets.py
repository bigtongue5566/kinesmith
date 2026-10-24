"""Optional Openverse discovery and conservative, auditable audio acquisition."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import time
import uuid
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
import soundfile as sf

from .model import inside, json_write

API = "https://api.openverse.org/v1/"
ALLOWED = {"cc0", "by"}


class RateLimited(RuntimeError):
    """A provider asks us to pause; callers can continue without external assets."""


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.port not in (None, 443) or parts.fragment):
        raise ValueError("download needs credential-free HTTPS on port 443")
    addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("private, loopback, metadata and non-public destinations are blocked")
    return url


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    value = response.headers.get("Retry-After")
    if value:
        try:
            return max(0, float(value))
        except ValueError:
            try:
                return max(0, parsedate_to_datetime(value).timestamp()-time.time())
            except (ValueError, TypeError):
                pass
    return 2**attempt


class Openverse:
    def __init__(self, cache: Path, *, client: httpx.Client | None = None, ttl: float = 86400,
                 min_interval: float = 1.1):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.client = client or httpx.Client(timeout=30, follow_redirects=False, trust_env=False)
        self.owned = client is None
        self.ttl, self.min_interval, self.last_request = ttl, min_interval, 0.0
        self.not_before = 0.0

    def close(self):
        if self.owned:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        if endpoint != "audio/" and endpoint != "rate_limit/":
            raise ValueError("unsupported Openverse endpoint")
        token = os.getenv("OPENVERSE_ACCESS_TOKEN")
        headers = {"User-Agent": "Opusmith/0.1 (local music asset discovery)"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        for attempt in range(3):
            pause = max(self.not_before-time.time(), self.min_interval-(time.monotonic()-self.last_request))
            if pause > 60:
                raise RateLimited(f"Openverse asks for a pause of {pause:.0f}s; resume later or synthesize")
            if pause > 0:
                time.sleep(pause)
            self.last_request = time.monotonic()
            try:
                response = self.client.get(API+endpoint, params=params, headers=headers)
            except httpx.TransportError:
                if attempt == 2:
                    raise
                self.not_before = time.time()+2**attempt
                continue
            # Preserve live quota headers; never treat a remembered request count as a specification.
            quotas = {k: v for k, v in response.headers.items() if "ratelimit" in k.lower()
                      or "rate-limit" in k.lower() or k.lower() == "retry-after"}
            json_write(self.cache/"rate-limit.json", {"checked_at": time.time(), "headers": quotas,
                       "status": response.status_code, "documentation": API})
            if response.status_code == 429 or response.status_code in (502, 503, 504):
                delay = _retry_delay(response, attempt)
                self.not_before = time.time()+delay
                if attempt == 2 or delay > 60:
                    raise RateLimited(f"Openverse HTTP {response.status_code}; retry after {delay:.0f}s")
                continue
            response.raise_for_status()
            # RateLimit-Remaining / Reset are provider-defined; only honor an unambiguous
            # delta reset when remaining is zero, and retain all raw headers for inspection.
            remaining = response.headers.get("x-ratelimit-remaining", response.headers.get("ratelimit-remaining"))
            reset = response.headers.get("ratelimit-reset")
            if remaining == "0" and reset:
                try:
                    self.not_before = time.time()+max(0, float(reset))
                except ValueError:
                    pass
            return response.json()
        raise RateLimited("Openverse unavailable")

    def limits(self) -> dict:
        return self._get("rate_limit/")

    def search(self, query: str, *, page_size: int = 10) -> dict:
        if not query.strip() or not 1 <= page_size <= 20:
            raise ValueError("search requires keywords and 1–20 candidates")
        params = {"q": query, "page_size": page_size, "license": "cc0,by"}
        key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        path = self.cache/f"{key}.json"
        if path.exists() and time.time()-path.stat().st_mtime < self.ttl:
            return json.loads(path.read_text(encoding="utf-8"))
        result = self._get("audio/", params)
        # Defensive filtering in addition to the provider's search filter.
        result["results"] = [r for r in result.get("results", []) if r.get("license") in ALLOWED]
        result["opusmith_notice"] = "候選素材，授權尚未核對；不得直接用於作品。"
        json_write(path, result)
        return result


def approved(record: dict) -> bool:
    """Evidence is a human/agent inspection record, not automatic legal certainty."""
    review = record.get("review", {})
    if record.get("license") not in ALLOWED:
        return False  # SA needs separate legal review outside this default publishing path.
    if record.get("license") == "by" and not record.get("creator"):
        return False
    version = record.get("license_version", "")
    expected = ("https://creativecommons.org/publicdomain/zero/1.0/"
                if record["license"] == "cc0" else f"https://creativecommons.org/licenses/by/{version}/")
    if (record.get("license_url", "").rstrip("/")+"/" != expected
            or (record["license"] == "cc0" and version != "1.0")
            or (record["license"] == "by" and version not in {"1.0", "2.0", "2.5", "3.0", "4.0"})):
        return False
    return bool(record.get("title") and record.get("source_url") and record.get("license_url")
                and review.get("status") == "verified" and review.get("checked_at")
                and review.get("reviewer") and review.get("evidence")
                and review.get("source_license_matches") is True)


def candidate_record(candidate: dict) -> dict:
    return {"title": candidate.get("title", ""), "creator": candidate.get("creator", ""),
            "source_url": candidate.get("foreign_landing_url", ""),
            "license": candidate.get("license", "unknown"),
            "license_version": candidate.get("license_version", ""),
            "license_url": candidate.get("license_url", ""),
            "download_url": candidate.get("url", ""), "openverse_id": candidate.get("id"),
            "quality_limitations": "原始品質尚未核對；若為壓縮預覽，須明確記錄。",
            "review": {"status": "pending"}, "modifications": [], "used_by_tracks": []}


def download(record: dict, root: Path, relative: str, *, max_bytes: int = 32*1024*1024,
             client: httpx.Client | None = None) -> dict:
    """Validate each redirect, cap streamed bytes, decode audio, then atomically save.

    DNS is checked before every request, but this is not a hardened DNS-pinning proxy.
    Use trusted HTTPS providers; untrusted multi-tenant network environments need egress controls.
    """
    if not approved(record):
        raise ValueError("original source/license must be independently verified before download")
    dest = inside(root, relative)
    if not relative.replace("\\", "/").startswith("assets/"):
        raise ValueError("store downloaded material under assets/")
    if dest.exists():
        raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(dest.name+f".{uuid.uuid4().hex}.part")
    owned = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=False, trust_env=False)
    try:
        url = record["download_url"]
        for _ in range(6):
            safe_url(url)
            with client.stream("GET", url, headers={"User-Agent": "Opusmith/0.1"}) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                if int(response.headers.get("content-length", 0)) > max_bytes:
                    raise ValueError("asset exceeds size limit")
                total = 0
                with temp.open("xb") as handle:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValueError("asset exceeds streamed size limit")
                        handle.write(chunk)
                info = sf.info(temp)
                if (info.frames <= 0 or not 8000 <= info.samplerate <= 192000
                        or info.channels not in (1, 2) or info.duration > 600):
                    raise ValueError("unsupported or excessive audio dimensions")
                # Decode in blocks: content-type and filename alone are not validation.
                import numpy as np

                with sf.SoundFile(temp) as audio:
                    for block in audio.blocks(blocksize=65536, dtype="float32", always_2d=True):
                        if not np.isfinite(block).all():
                            raise ValueError("nonfinite downloaded audio")
                temp.replace(dest)
                from .project import sha

                return {**record, "file": relative.replace("\\", "/"), "sha256": sha(dest),
                        "downloaded_at": datetime.now(UTC).isoformat(),
                        "final_download_url": url, "bytes": total,
                        "audio": {"duration": info.duration, "sample_rate": info.samplerate,
                                  "channels": info.channels, "format": info.format}}
        raise ValueError("too many redirects")
    finally:
        temp.unlink(missing_ok=True)
        if owned:
            client.close()


def write_credits(path: Path, records: list[dict]):
    lines = ["# 音訊素材來源與署名", ""]
    if not records:
        lines += ["本作品未使用外部素材；音訊由本地合成器產生。"]
    for r in records:
        lines += [f"## {r.get('title', '未命名素材')}", "",
                  f"作者：{r.get('creator', '未提供')}；來源：{r.get('source_url', '')}",
                  f"授權：{r.get('license', 'unknown')} {r.get('license_version', '')} · "
                  f"{r.get('license_url', '')}",
                  f"檔案：{r.get('file', '尚未下載')}；SHA-256：{r.get('sha256', '—')}",
                  f"下載：{r.get('downloaded_at', '—')}；URL：{r.get('download_url', '')}",
                  f"修改：{'; '.join(r.get('modifications', [])) or '無'}",
                  f"使用音軌：{', '.join(r.get('used_by_tracks', [])) or '未使用'}",
                  f"品質限制：{r.get('quality_limitations', '尚未記錄')}",
                  f"授權核對：{json.dumps(r.get('review', {}), ensure_ascii=False)}", ""]
    path.write_text("\n".join(lines)+"\n", encoding="utf-8")
