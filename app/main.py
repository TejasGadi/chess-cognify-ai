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


@app.on_event("startup")
async def startup_event():
    """Run application startup tasks."""
    logger.info("Running typical startup tasks...")
    # Seed model configurations from env vars on first run
    from app.models.base import SessionLocal
    from app.models.model_config import ModelConfig
    from app.utils.crypto import encrypt_api_key
    
    db = SessionLocal()
    try:
        # Check if configs already exist
        existing_configs = db.query(ModelConfig).count()
        if existing_configs == 0 and settings.openai_api_key:
            logger.info("No model configs found. Bootstrapping from environment variables...")
            
            encrypted_key = encrypt_api_key(settings.openai_api_key)
            
            # Setup LLM, Vision, Embedding defaults using OpenAI
            llm_config = ModelConfig(
                config_type="llm", provider="openai",
                model_name=settings.openai_model, api_key_encrypted=encrypted_key, is_active=True
            )
            vision_config = ModelConfig(
                config_type="vision", provider="openai",
                model_name=settings.openai_vision_model, api_key_encrypted=encrypted_key, is_active=True
            )
            embedding_config = ModelConfig(
                config_type="embedding", provider="openai",
                model_name=settings.openai_embedding_model, api_key_encrypted=encrypted_key, is_active=True
            )
            
            db.add_all([llm_config, vision_config, embedding_config])
            db.commit()
            logger.info("Successfully bootstrapped default OpenAI configurations.")
    except Exception as e:
        logger.error(f"Error bootstrapping model configs: {e}")
    finally:
        db.close()


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
from app.api.model_config import router as model_config_router

app.include_router(games_router)
app.include_router(books_router)
app.include_router(chat_router)
app.include_router(status_router)
app.include_router(evaluate_router)
app.include_router(model_config_router)

# Mount static files for book images
app.mount("/api/book_images", StaticFiles(directory=IMAGE_DIR), name="book_images")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down application...")
    shutdown_langfuse()
    
    # Cleanup Stockfish engine
    try:
        from app.services.stockfish_service import get_stockfish_service
        service = await get_stockfish_service()
        await service.close()
    except Exception as e:
        logger.error(f"Error closing Stockfish engine: {e}")
        
    logger.info("Application shutdown complete")