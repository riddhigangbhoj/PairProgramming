"""
Autocomplete endpoints.
Handles AI-powered code completion suggestions.
"""

from fastapi import APIRouter, HTTPException, status
import logging

from app.models import AutocompleteRequest, AutocompleteResponse
from app.services.autocomplete_service import AutocompleteService
from app.config import settings


router = APIRouter()
autocomplete_service = AutocompleteService()
logger = logging.getLogger(__name__)


@router.post("/", response_model=AutocompleteResponse)
async def get_autocomplete_suggestions(request: AutocompleteRequest):
    """
    Get AI-powered autocomplete suggestions for code.
    - **code**: Current code context
    - **cursor_position**: Current cursor position
    - **language**: Programming language (default: python)
    
    Returns list of suggestions with confidence score.
    """
    try:
        logger.debug(
            f"Autocomplete request for {request.language} at position {request.cursor_position}"
        )

        suggestions = autocomplete_service.get_suggestions(
            code=request.code,
            cursor_position=request.cursor_position,
            language=request.language
        )

        logger.info(
            f"Generated {len(suggestions.suggestions)} suggestions "
            f"with confidence {suggestions.confidence}"
        )

        return suggestions

    except ValueError as e:
        # Handle expected validation errors
        logger.warning(f"Invalid autocomplete request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request parameters"
        )

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Autocomplete error: {str(e)}", exc_info=True)

        # Security: Hide error details in production
        detail = (
            f"Error generating autocomplete suggestions: {str(e)}"
            if settings.DEBUG
            else "Error generating autocomplete suggestions"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )