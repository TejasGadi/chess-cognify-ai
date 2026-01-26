"""
Custom exception handlers for the API.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """
    Handle Pydantic validation errors.

    Returns user-friendly error messages.
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(f"Validation error on {request.url.path}: {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "message": "Invalid request data",
            "details": errors,
        },
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Handle database errors.

    Returns generic error message without exposing database details.
    """
    logger.error(f"Database error on {request.url.path}: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database error",
            "message": "An error occurred while processing your request. Please try again later.",
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions.

    Logs the error and returns a generic message.
    """
    logger.error(
        f"Unexpected error on {request.url.path}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )
