"""轻量同步 HTTP 工具（urllib），供各数据源连接器使用。"""
import json as _json
import urllib.request
import urllib.parse

DEFAULT_UA = "AI-BOS/1.0 (company intelligence research; contact: admin@ai-bos.local)"


def http_get(url: str, headers: dict | None = None, timeout: int = 20) -> bytes:
    h = {"User-Agent": DEFAULT_UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url: str, headers: dict | None = None, timeout: int = 20):
    return _json.loads(http_get(url, headers, timeout).decode("utf-8", errors="replace"))


def post_json(url: str, data: dict, headers: dict | None = None, timeout: int = 20):
    body = urllib.parse.urlencode(data).encode()
    h = {"User-Agent": DEFAULT_UA, "Content-Type": "application/x-www-form-urlencoded"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return _json.loads(r.read().decode("utf-8", errors="replace"))
