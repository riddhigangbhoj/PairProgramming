"""
Main FastAPI application entry point.
Initializes the app, middleware, and routes.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import sys

from app.database import engine
from app.models import Base
from app.routes import rooms, autocomplete, websocket
from app.config import settings
from app.middleware import SecurityHeadersMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Events (Modern FastAPI approach)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events using modern lifespan context manager.
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown")
    """
    # Startup
    logger.info("🚀 Starting Pair Programming App...")

    # Initialize database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    if settings.DEBUG:
        logger.warning("⚠️  Running in DEBUG mode - DO NOT use in production!")
        logger.info(f"CORS enabled for origins: {settings.ALLOWED_ORIGINS}")
    else:
        logger.info("Running in PRODUCTION mode")

    logger.info("✅ Application startup complete")

    yield  # Application runs here

    # Shutdown
    logger.info("👋 Shutting down Pair Programming App...")
    logger.info("✅ Shutdown complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Pair Programming App",
    description="Real-time collaborative coding platform with AI-powered autocomplete",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
)


# ============================================================================
# Global Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages"""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to prevent stack trace leaks"""
    logger.error(f"Unhandled exception on {request.url}: {str(exc)}", exc_info=True)

    if settings.DEBUG:
        # Show details in development
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        # Hide details in production
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )


# ============================================================================
# Middleware
# ============================================================================

# Security headers middleware (apply first)
if not settings.DEBUG:
    app.add_middleware(SecurityHeadersMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# ============================================================================
# Route Inclusion
# ============================================================================

app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(autocomplete.router, prefix="/autocomplete", tags=["autocomplete"])
app.include_router(websocket.router, tags=["websocket"])


# ============================================================================
# Root & Health Check Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint with basic information"""
    return {
        "message": "Welcome to Pair Programming App API",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production",
        "health": "/health",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "debug": settings.DEBUG
    }
