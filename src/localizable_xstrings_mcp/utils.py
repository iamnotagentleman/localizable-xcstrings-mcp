import os
from typing import Dict, Any


def validate_xcstrings_file(file_path: str) -> bool:
    """
    Validate if a file exists and has the .xcstrings extension.
    
    Args:
        file_path (str): Path to check
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    if not file_path.lower().endswith('.xcstrings'):
        return False
    
    return True


def validate_language_code(language_code: str) -> bool:
    """
    Basic validation for language codes.
    
    Args:
        language_code (str): Language code to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not language_code or not isinstance(language_code, str):
        return False
    
    # Basic validation: 2-5 characters, letters and hyphens only
    if len(language_code) < 2 or len(language_code) > 5:
        return False
    
    return all(c.isalpha() or c == '-' for c in language_code)


def format_error_message(error: Exception, context: str = "") -> str:
    """
    Format error messages consistently.
    
    Args:
        error (Exception): The exception to format
        context (str): Additional context for the error
        
    Returns:
        str: Formatted error message
    """
    if context:
        return f"{context}: {str(error)}"
    return str(error)