import logging

from xcstrings_tools import (
    get_supported_languages,
    get_base_language_strings,
    extract_base_keys,
    translate_strings,
    translate_and_apply,
    apply_missing_translations,
    translate_single_key
)
from utils import validate_xcstrings_file, validate_language_code, format_error_message
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("xcstrings-mcp")

@mcp.tool()
def get_languages_tool(file_path: str) -> str:
    """
    MCP tool to get supported languages from xcstrings file.

    Args:
        file_path (str): Path to the .xcstrings file

    Returns:
        str: JSON string of supported languages or error message
    """
    try:
        if not validate_xcstrings_file(file_path):
            return f"Error: Invalid file path or not an .xcstrings file: {file_path}"

        languages = get_supported_languages(file_path)
        return f"Supported languages: {', '.join(languages)}"
    except Exception as e:
        return format_error_message(e, "Failed to get supported languages")
@mcp.tool()
def get_keys_tool(file_path: str) -> str:
    """
    MCP tool to get all localization keys from xcstrings file.

    Args:
        file_path (str): Path to the .xcstrings file

    Returns:
        str: List of all keys or error message
    """
    try:
        if not validate_xcstrings_file(file_path):
            return f"Error: Invalid file path or not an .xcstrings file: {file_path}"

        keys = extract_base_keys(file_path)
        return f"Found {len(keys)} keys:\n" + "\n".join(keys)
    except Exception as e:
        return format_error_message(e, "Failed to get keys")
@mcp.tool()
def get_base_strings_tool(file_path: str) -> str:
    """
    MCP tool to get base language strings from xcstrings file.

    Args:
        file_path (str): Path to the .xcstrings file

    Returns:
        str: Base language strings or error message
    """
    try:
        if not validate_xcstrings_file(file_path):
            return f"Error: Invalid file path or not an .xcstrings file: {file_path}"

        keys = get_base_language_strings(file_path)

        return f"Base language keys ({len(keys)} total):\n" + "\n".join(keys)
    except Exception as e:
        return format_error_message(e, "Failed to get base language strings")

@mcp.tool()
def translate_tool(file_path: str, target_language: str) -> str:
    """
    MCP tool to translate strings to target language and return translated keys.

    Args:
        file_path (str): Path to the .xcstrings file
        target_language (str): Target language code

    Returns:
        str: Translation result with translated keys or error message
    """
    try:
        if not validate_xcstrings_file(file_path):
            return f"Error: Invalid file path or not an .xcstrings file: {file_path}"

        if not validate_language_code(target_language):
            return f"Error: Invalid language code: {target_language}"

        # Get base keys
        base_keys = get_base_language_strings(file_path)
        if not base_keys:
            return "Error: No base language keys found"

        # Translate
        translated, skipped = translate_strings(base_keys, target_language)
        if not translated and not skipped:
            return "Error: Translation failed or returned no results"

        result = []
        if translated:
            result.append(f"Translated {len(translated)} strings to {target_language}:")
            for key, value in translated.items():
                result.append(f"{key}: {value}")
        
        if skipped:
            result.append(f"\nSkipped {len(skipped)} strings:")
            for key, reason in skipped.items():
                result.append(f"{key}: {reason}")
        
        return "\n".join(result)
    except Exception as e:
        return format_error_message(e, "Translation failed")

@mcp.tool()
def apply_tool(file_path: str, target_language: str, app_description: str = "") -> str:
    """
    MCP tool to translate and apply translations to xcstrings file.

    Args:
        file_path (str): Path to the .xcstrings file
        target_language (str): Target language code
        app_description (str): Optional description of the app for better translation context

    Returns:
        str: Application result with translated keys or error message
    """
    try:
        if not validate_xcstrings_file(file_path):
            return f"Error: Invalid file path or not an .xcstrings file: {file_path}"

        if not validate_language_code(target_language):
            return f"Error: Invalid language code: {target_language}"

        # Check if target language already exists
        supported_languages = get_supported_languages(file_path)
        
        if target_language in supported_languages:
            warning_msg = f"Warning: {target_language} translations already exist in this file.\n"
            warning_msg += f"Using apply_tool will overwrite existing translations.\n"
            warning_msg += f"Consider using apply_missing_tool instead to only translate missing keys.\n\n"
            return warning_msg
        else:
            warning_msg = ""

        # Translate and apply in one step
        app_desc = app_description if app_description else None
        applied_translations, backup_path, summary, skipped_keys = translate_and_apply(file_path, target_language, app_description=app_desc)
        if not applied_translations and not skipped_keys:
            return "Error: Translation failed or returned no results"

        result = [
            f"Summary: {summary}",
            f"Backup created: {backup_path}",
        ]
        
        if applied_translations:
            result.append(f"\nTranslated strings ({len(applied_translations)}):\n")
            for key, value in applied_translations.items():
                result.append(f"{key}: {value}")
        
        if skipped_keys:
            result.append(f"\n\nSkipped strings ({len(skipped_keys)}):\n")
            for key, reason in skipped_keys.items():
                result.append(f"{key}: {reason}")
        
        return "\n".join(result)

    except Exception as e:
        return format_error_message(e, "Failed to apply translations")

@mcp.tool()
def apply_missing_tool(file_path: str, target_language: str, app_description: str = "") -> str:
    """
    MCP tool to apply only missing translations for a target language in xcstrings file.
    Only translates keys that don't already have translations in the target language.

    Args:
        file_path (str): Path to the .xcstrings file
        target_language (str): Target language code
        app_description (str): Optional description of the app for better translation context

    Returns:
        str: Application result with newly translated keys or error message
    """
    try:
        if not validate_xcstrings_file(file_path):
            return f"Error: Invalid file path or not an .xcstrings file: {file_path}"

        if not validate_language_code(target_language):
            return f"Error: Invalid language code: {target_language}"

        # Apply only missing translations
        app_desc = app_description if app_description else None
        applied_translations, backup_path, summary, skipped_keys = apply_missing_translations(file_path, target_language, app_description=app_desc)
        
        result = [
            f"Summary: {summary}",
        ]
        
        if backup_path:
            result.append(f"Backup created: {backup_path}")
        
        if applied_translations:
            result.append(f"\nNew translations added ({len(applied_translations)}):")
            for key, value in applied_translations.items():
                result.append(f"{key}: {value}")
        
        if skipped_keys:
            result.append(f"\nSkipped strings ({len(skipped_keys)}):")
            for key, reason in skipped_keys.items():
                result.append(f"{key}: {reason}")
        
        return "\n".join(result)

    except Exception as e:
        return format_error_message(e, "Failed to apply missing translations")

@mcp.tool()
def translate_key_tool(file_path: str, key: str, target_languages: str, app_description: str = "") -> str:
    """
    MCP tool to translate a specific key to multiple target languages and apply translations.

    Args:
        file_path (str): Path to the .xcstrings file
        key (str): The specific key to translate
        target_languages (str): Comma-separated list of target language codes (e.g., "es,fr,de")
        app_description (str): Optional description of the app for better translation context

    Returns:
        str: Translation results or error message
    """
    try:
        if not validate_xcstrings_file(file_path):
            return f"Error: Invalid file path or not an .xcstrings file: {file_path}"

        # Parse target languages
        languages = [lang.strip() for lang in target_languages.split(',') if lang.strip()]
        if not languages:
            return "Error: No target languages provided"

        # Validate all language codes
        for lang in languages:
            if not validate_language_code(lang):
                return f"Error: Invalid language code: {lang}"

        # Translate the key
        app_desc = app_description if app_description else None
        translations, backup_path, errors = translate_single_key(
            file_path, key, languages, app_description=app_desc
        )

        if not translations and errors:
            return f"Error: All translations failed:\n" + "\n".join(
                f"{lang}: {error}" for lang, error in errors.items()
            )

        result = [
            f"Translated key '{key}' to {len(translations)} language(s)",
            f"Backup created: {backup_path}",
        ]

        if translations:
            result.append("\nSuccessful translations:")
            for lang, trans_dict in translations.items():
                for k, value in trans_dict.items():
                    result.append(f"  {lang}: {value}")

        if errors:
            result.append("\nFailed translations:")
            for lang, error in errors.items():
                result.append(f"  {lang}: {error}")

        return "\n".join(result)

    except KeyError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return format_error_message(e, "Failed to translate key")


if __name__ == "__main__":
    logging.info("Starting localizable xcstrings mcp server")
    mcp.run()