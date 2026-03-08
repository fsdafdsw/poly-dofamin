import json
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 20,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    query = urlencode(_stringify_dict(params or {}))
    final_url = url if not query else "{0}?{1}".format(url, query)
    request = Request(final_url, headers=headers or {}, method="GET")
    return _send_json_request(request=request, timeout=timeout)


def post_form(
    url: str,
    data: Dict[str, Any],
    timeout: int = 20,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    encoded = urlencode(_stringify_dict(data)).encode("utf-8")
    merged_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if headers:
        merged_headers.update(headers)
    request = Request(url, data=encoded, headers=merged_headers, method="POST")
    return _send_json_request(request=request, timeout=timeout)


def _send_json_request(request: Request, timeout: int) -> Any:
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError("HTTP {0} for {1}: {2}".format(exc.code, request.full_url, body)) from exc
    except URLError as exc:
        raise RuntimeError("Network error for {0}: {1}".format(request.full_url, exc.reason)) from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid JSON response from {0}".format(request.full_url)) from exc


def _stringify_dict(data: Dict[str, Any]) -> Dict[str, str]:
    return {str(key): str(value) for key, value in data.items()}
