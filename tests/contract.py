"""Тонка обгортка над openapi-core: валідує відповідь httpx проти openapi.yaml
і падає з коротким читабельним повідомленням «поле → причина»."""

from openapi_core import OpenAPI
from openapi_core.datatypes import RequestParameters

MAX_LINES = 3  # щоб вивід влазив на слайд


class _Request:
    def __init__(self, host_url, response):
        self.host_url = host_url
        self.path = response.request.url.path
        self.method = response.request.method.lower()
        self.body = response.request.content or None
        self.content_type = response.request.headers.get("content-type", "application/json")
        self.parameters = RequestParameters()


class _Response:
    def __init__(self, response):
        self.status_code = response.status_code
        self.data = response.content
        self.content_type = response.headers.get("content-type", "")
        self.headers = response.headers


def _schema_errors(exc):
    """Шукає помилки jsonschema у ланцюжку винятків openapi-core."""
    while exc is not None:
        errors = getattr(exc, "schema_errors", None)
        if errors:
            return errors
        exc = exc.__cause__ or exc.__context__
    return []


def _field_path(error):
    parts = ["$"]
    for part in error.absolute_path:
        parts.append(f"[{part}]" if isinstance(part, int) else f".{part}")
    return "".join(parts)


class Contract:
    def __init__(self, spec_path, host_url):
        self.openapi = OpenAPI.from_file_path(str(spec_path))
        self.host_url = host_url

    def validate(self, response):
        try:
            self.openapi.validate_response(_Request(self.host_url, response), _Response(response))
        except Exception as exc:
            request = response.request
            lines = [f"{request.method} {request.url.path} -> {response.status_code}: "
                     f"відповідь не відповідає контракту"]
            errors = _schema_errors(exc)
            if errors:
                lines += [f"  {_field_path(e)}: {e.message}" for e in errors[:MAX_LINES]]
                if len(errors) > MAX_LINES:
                    lines.append(f"  ... і ще {len(errors) - MAX_LINES} таких самих")
            else:
                lines.append(f"  {exc}")
            raise AssertionError("\n".join(lines)) from None
