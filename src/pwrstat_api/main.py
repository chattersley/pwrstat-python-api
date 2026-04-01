import logging
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .parser import PwrstatError, get_pwrstat_status

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    binary = Path("/usr/sbin/pwrstat")
    if not binary.is_file():
        logger.warning("pwrstat binary not found at %s — requests will fail", binary)
    yield


app = FastAPI(
    title="pwrstat API",
    description="REST API for CyberPower UPS status via pwrstat",
    version="1.0.0",
    lifespan=lifespan,
    # Disable auto-generated docs in production if desired; left on for convenience.
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get(
    "/pwrstat",
    summary="UPS status",
    response_description="Key-value map of all UPS parameters",
)
@limiter.limit("60/minute")
async def get_pwrstat(request: Request) -> dict[str, str]:
    """Returns the current UPS status as reported by `pwrstat -status`."""
    try:
        status = get_pwrstat_status()
    except FileNotFoundError:
        logger.error("pwrstat binary not found")
        raise HTTPException(status_code=503, detail="UPS service unavailable") from None
    except subprocess.TimeoutExpired:
        logger.error("pwrstat command timed out")
        raise HTTPException(status_code=503, detail="UPS service timed out") from None
    except PwrstatError as exc:
        logger.error("pwrstat error: %s", exc)
        raise HTTPException(status_code=503, detail="UPS service unavailable") from None
    except Exception:
        logger.exception("Unexpected error reading pwrstat")
        raise HTTPException(status_code=500, detail="Internal server error") from None

    if not status:
        raise HTTPException(status_code=503, detail="No UPS data available")

    return status


def run() -> None:
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
    port = int(os.environ.get("PORT", "5002"))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()

    uvicorn.run(
        "pwrstat_api.main:app",
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    run()
