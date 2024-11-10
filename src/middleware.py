import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import utils
from exceptions import HTTPException

logger = utils.get_logger(__name__)


class LoggerMiddleware(BaseHTTPMiddleware):
    """
    This middleware catches error and return the appropriate response
    It also send an info log with useful information for every request
    """

    # some endpoints don't require any logging
    # they should be added to this set
    excluded_paths = {"/ping"}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ):
        status_code = 200
        start = time.time()
        try:
            res = await call_next(request)
            status_code = res.status_code
            return res
        except HTTPException as err:
            # specific application errors
            # Those errors are expected, and don't require any logging
            status_code = err.http_status
            return JSONResponse(
                {"error": "NOT_FOUND", "message": str(err)}, status_code=status_code
            )
        except Exception as _:
            # Unexpected errors
            status_code = 500
            logger.exception(
                utils.server_log_message(request, status_code),
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                },
            )
            return JSONResponse(
                {"error": "INTERNAL_ERROR", "message": "Oops! Something went wrong!"},
                status_code=status_code,
            )
        finally:
            if request.url.path not in self.excluded_paths:
                # information logs with request & response details
                logger.info(
                    utils.server_log_message(request, status_code),
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "latency": time.time() - start,
                    },
                )
