"""
FastAPI application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
from app.utils.logger import setup_logging, get_logger
from app.utils.langfuse_handler import initialize_langfuse, shutdown_langfuse
from app.api.exceptions import (
    validation_exception_handler,
    database_exception_handler,
    general_exception_handler,
)

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Initialize Langfuse for observability
initialize_langfuse()

# Create FastAPI app
app = FastAPI(
    title="AI Chess Game Review Coach",
    description="Stockfish-powered chess analysis with AI explanations",
    version="0.1.0",
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Chess Game Review Coach API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns simple health status. For detailed system status, use /api/status.
    """
    return {"status": "healthy"}


from fastapi.staticfiles import StaticFiles
import os

# Ensure image directory exists
IMAGE_DIR = "uploads/book_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# Include routers
from app.api.games import router as games_router
from app.api.chat import router as chat_router
from app.api.books import router as books_router
from app.api.status import status_router
from app.api.evaluate import router as evaluate_router

app.include_router(games_router)
app.include_router(books_router)
app.include_router(chat_router)
app.include_router(status_router)
app.include_router(evaluate_router)

# Mount static files for book images
app.mount("/api/book_images", StaticFiles(directory=IMAGE_DIR), name="book_images")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down application...")
    shutdown_langfuse()
    logger.info("Application shutdown complete")