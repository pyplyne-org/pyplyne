from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"
PYPLYNE_URL_ENV = "PYPLYNE_URL"


@dataclass(frozen=True)
class PyPlyneClientResponse:
    status: int
    body: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def send_source(
    source: str,
    *,
    url: str | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    json_output: bool = False,
    filename: str | None = None,
    timeout: float = 30,
) -> PyPlyneClientResponse:
    endpoint = run_endpoint(
        url=url, host=host, port=port, json_output=json_output, filename=filename
    )
    request = Request(
        endpoint,
        data=source.encode("utf-8"),
        method="POST",
        headers={"Accept": "application/json" if json_output else "text/plain"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return PyPlyneClientResponse(
                status=response.status,
                body=response.read().decode("utf-8"),
            )
    except HTTPError as exc:
        return PyPlyneClientResponse(
            status=exc.status,
            body=exc.read().decode("utf-8"),
        )


def run_endpoint(
    *,
    url: str | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    json_output: bool = False,
    filename: str | None = None,
) -> str:
    base = url or os.environ.get(PYPLYNE_URL_ENV) or f"http://{host}:{port}"
    if "://" not in base:
        base = f"http://{base}"
    parsed = urlparse(base)
    path = parsed.path.rstrip("/")
    if not path.endswith("/run"):
        path = f"{path}/run" if path else "/run"

    query = dict(parse_qsl(parsed.query))
    if json_output:
        query["format"] = "json"
    if filename:
        query["filename"] = filename

    return urlunparse(
        (
            parsed.scheme or "http",
            parsed.netloc,
            path,
            parsed.params,
            urlencode(query),
            parsed.fragment,
        )
    )
