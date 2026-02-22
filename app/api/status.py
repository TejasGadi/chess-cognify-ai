"""
System status and health check endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.base import get_db
from app.config import settings
from app.utils.logger import get_logger
from typing import Dict, Any
import httpx
import redis

logger = get_logger(__name__)

status_router = APIRouter(prefix="/api", tags=["status"])


@status_router.get("/status")
async def get_system_status(db: Session = Depends(get_db)):
    """
    Get comprehensive system status including all services.

    Checks:
    - Database connectivity
    - Redis cache
    - Qdrant vector database
    - Ollama embeddings
    - OpenAI LLM API
    - Stockfish engine
    """
    status_info: Dict[str, Any] = {
        "status": "healthy",
        "services": {},
    }

    # Check PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        status_info["services"]["postgresql"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except Exception as e:
        status_info["status"] = "degraded"
        status_info["services"]["postgresql"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }

    # Check Redis
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        status_info["services"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful",
        }
    except Exception as e:
        status_info["status"] = "degraded"
        status_info["services"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}",
        }

    # Check Qdrant
    try:
        async with httpx.AsyncClient() as client:
            # Qdrant health check endpoint
            response = await client.get(
                f"{settings.qdrant_url}/healthz",
                timeout=5.0,
            )
            if response.status_code == 200:
                status_info["services"]["qdrant"] = {
                    "status": "healthy",
                    "message": "Qdrant is accessible",
                }
            else:
                status_info["status"] = "degraded"
                status_info["services"]["qdrant"] = {
                    "status": "unhealthy",
                    "message": f"Qdrant returned status {response.status_code}",
                }
    except Exception as e:
        status_info["status"] = "degraded"
        status_info["services"]["qdrant"] = {
            "status": "unhealthy",
            "message": f"Qdrant connection failed: {str(e)}",
        }

    # Check Ollama
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=5.0,
            )
            if response.status_code == 200:
                status_info["services"]["ollama"] = {
                    "status": "healthy",
                    "message": "Ollama is accessible",
                    "model": settings.ollama_embedding_model,
                }
            else:
                status_info["status"] = "degraded"
                status_info["services"]["ollama"] = {
                    "status": "unhealthy",
                    "message": f"Ollama returned status {response.status_code}",
                }
    except Exception as e:
        status_info["status"] = "degraded"
        status_info["services"]["ollama"] = {
            "status": "unhealthy",
            "message": f"Ollama connection failed: {str(e)}",
        }

    # Check OpenAI API (Primary)
    try:
        if settings.openai_api_key:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    timeout=5.0,
                )
                if response.status_code == 200:
                    status_info["services"]["openai"] = {
                        "status": "healthy",
                        "message": "OpenAI API is accessible",
                        "model": settings.openai_model,
                        "vision_model": settings.openai_vision_model,
                    }
                else:
                    status_info["status"] = "degraded"
                    status_info["services"]["openai"] = {
                        "status": "unhealthy",
                        "message": f"OpenAI API returned status {response.status_code}",
                    }
        else:
            status_info["status"] = "degraded"
            status_info["services"]["openai"] = {
                "status": "unhealthy",
                "message": "OpenAI API key not configured",
            }
    except Exception as e:
        status_info["status"] = "degraded"
        status_info["services"]["openai"] = {
            "status": "unhealthy",
            "message": f"OpenAI API connection failed: {str(e)}",
        }


    # Check Stockfish
    try:
        import subprocess
        import os
        import shutil

        # Try to find stockfish in common locations (include Docker/Debian path)
        stockfish_paths = [
            settings.stockfish_path,
            "/usr/games/stockfish",  # Debian/Ubuntu apt in Docker
            "/usr/local/bin/stockfish",
            "/usr/bin/stockfish",
            shutil.which("stockfish") or "",
        ]
        
        stockfish_found = None
        for path in stockfish_paths:
            if path and os.path.exists(path):
                stockfish_found = path
                break
        
        if stockfish_found:
            # Try to run stockfish
            try:
                process = subprocess.Popen(
                    [stockfish_found],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                process.stdin.write(b"uci\n")
                process.stdin.flush()
                process.terminate()
                process.wait(timeout=2)

                status_info["services"]["stockfish"] = {
                    "status": "healthy",
                    "message": "Stockfish engine is accessible",
                    "path": stockfish_found,
                }
            except Exception as e:
                status_info["status"] = "degraded"
                status_info["services"]["stockfish"] = {
                    "status": "unhealthy",
                    "message": f"Stockfish found but failed to run: {str(e)}",
                    "path": stockfish_found,
                }
        else:
            status_info["status"] = "degraded"
            status_info["services"]["stockfish"] = {
                "status": "unhealthy",
                "message": f"Stockfish not found. Checked: {', '.join([p for p in stockfish_paths if p])}. Set STOCKFISH_PATH env var to specify location.",
            }
    except Exception as e:
        status_info["status"] = "degraded"
        status_info["services"]["stockfish"] = {
            "status": "unhealthy",
            "message": f"Stockfish check failed: {str(e)}",
        }

    # Determine overall status
    unhealthy_count = sum(
        1
        for service in status_info["services"].values()
        if service.get("status") == "unhealthy"
    )

    if unhealthy_count > 0:
        status_info["status"] = "degraded" if unhealthy_count < len(
            status_info["services"]
        ) else "unhealthy"

    return status_info


@status_router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """
    Get basic system metrics.

    Returns:
    - Total games analyzed
    - Total books uploaded
    - Cache statistics (if available)
    """
    try:
        from app.models.game import Game, GameSummary
        from app.models.book import Book

        total_games = db.query(Game).count()
        analyzed_games = db.query(GameSummary).count()
        total_books = db.query(Book).count()

        metrics = {
            "games": {
                "total": total_games,
                "analyzed": analyzed_games,
            },
            "books": {
                "total": total_books,
            },
        }

        # Try to get Redis cache stats
        try:
            redis_client = redis.from_url(settings.redis_url)
            info = redis_client.info()
            metrics["cache"] = {
                "status": "available",
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception:
            metrics["cache"] = {
                "status": "unavailable",
            }

        return metrics

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")
