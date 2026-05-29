import json
import urllib.error
import urllib.request

from fastapi import APIRouter

from backend.app.core.config import get_settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/llm")
def llm_health_check() -> dict[str, object]:
    settings = get_settings()
    if not settings.openai_api_key:
        return {
            "configured": False,
            "ok": False,
            "model": settings.openai_chat_model,
            "error": "missing_openai_api_key",
        }

    payload = {
        "model": settings.openai_chat_model,
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "temperature": 0,
        "max_tokens": 5,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        return {
            "configured": True,
            "ok": True,
            "model": settings.openai_chat_model,
            "sample": body["choices"][0]["message"]["content"],
        }
    except Exception as exc:
        error = _safe_openai_error(exc)
        print(f"LLM health check failed: {type(exc).__name__}: {error}")
        return {
            "configured": True,
            "ok": False,
            "model": settings.openai_chat_model,
            "error": error,
        }


def _safe_openai_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            error = json.loads(body).get("error", {})
            code = error.get("code") or error.get("type") or "http_error"
            return f"{code} (HTTP {exc.code})"
        except Exception:
            return f"HTTPError (HTTP {exc.code})"
    return type(exc).__name__
