import json
import os
import asyncio
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from openai import AsyncOpenAI
from concurrent.futures import ThreadPoolExecutor

from settings import settings


def extract_placeholders(text: str) -> List[str]:
    """Extract iOS placeholders from a string."""
    import re
    # Match iOS placeholders like %@, %lld, %d, %f, etc.
    # Also match positional ones like %1$@ to detect unwanted modifications
    pattern = r'%(?:\d+\$)?(?:@|lld|ld|d|f|s|u|i|o|x|X|e|E|g|G|c|C|p|a|A|F)'
    return re.findall(pattern, text)


def get_supported_languages(file_path: str) -> List[str]:
    """
    Extract supported language codes from a Localizable.xcstrings file.
    
    Args:
        file_path (str): Path to the .xcstrings file
        
    Returns:
        List[str]: List of supported language codes
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
        KeyError: If the file doesn't have the expected structure
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    languages = set()
    
    # Add source language
    if 'sourceLanguage' in data:
        languages.add(data['sourceLanguage'])
    
    # Extract languages from localizations
    if 'strings' in data:
        for key, value in data['strings'].items():
            if 'localizations' in value:
                languages.update(value['localizations'].keys())
    
    return sorted(list(languages))


def extract_base_keys(file_path: str) -> List[str]:
    """
    Extract all string keys from a Localizable.xcstrings file.
    
    Args:
        file_path (str): Path to the .xcstrings file
        
    Returns:
        List[str]: List of all string keys
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
        KeyError: If the file doesn't have the expected structure
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'strings' not in data:
        return []
    
    return list(data['strings'].keys())


def get_base_language_strings(file_path: str) -> List[str]:
    """
    Extract all string keys from a Localizable.xcstrings file.
    
    Args:
        file_path (str): Path to the .xcstrings file
        
    Returns:
        List[str]: List of string keys to translate
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
        KeyError: If the file doesn't have the expected structure
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'strings' not in data:
        return []
        
    return list(data['strings'].keys())



async def translate_chunk_async(
    strings_chunk: Dict[str, str],
    target_language: str,
    source_language: str = "en",
    app_description: Optional[str] = None
) -> Dict[str, str]:
    """
    Translate a chunk of strings asynchronously using OpenRouter API.
    
    Args:
        strings_chunk (Dict[str, str]): Chunk of key-value pairs to translate
        target_language (str): Target language code
        source_language (str): Source language code
        app_description (Optional[str]): Optional description of the app for better translation context
        
    Returns:
        Dict[str, str]: Dictionary of translated key-value pairs
    """
    if not strings_chunk:
        return {}
    
    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    
    # Prepare the translation request
    print(f"Processing chunk with {len(strings_chunk)} strings")
    
    # Convert strings to JSON for the prompt
    strings_json = json.dumps(strings_chunk, ensure_ascii=False, indent=2)
    
    # Build comprehensive system prompt
    system_prompt = f"""You are a professional iOS app translator specializing in UI/UX localization.{' You are translating for: ' + app_description if app_description else 'an app'}

Your task is to translate app interface strings from {source_language} to {target_language}.

INSTRUCTIONS:
1. Return a JSON object with the exact same structure as the input
2. Keys remain UNCHANGED (they are string identifiers)
3. Values are TRANSLATED to {target_language}
4. Include ALL {len(strings_chunk)} keys from the input

CRITICAL RULES FOR iOS PLACEHOLDERS:
- Keep %@ as %@ (NOT %1$@ or %s)
- Keep %lld as %lld (NOT %1$lld or %d)
- Keep %d as %d (NOT %1$d)
- Keep all other placeholders UNCHANGED
- Do NOT add positional indicators like %1$, %2$, etc.
- The order and format of placeholders must remain EXACTLY the same

Example input: {{"welcome": "Hello %@", "%lld job%@": "%lld job%@"}}
Example output: {{"welcome": "Hola %@", "%lld job%@": "%lld trabajo%@"}}

Use appropriate terminology for the app domain. Always respond with valid JSON only."""

    # Simple user prompt with just the data
    user_prompt = f"Translate this JSON to {target_language}:\n{strings_json}"
    
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=settings.translation_temperature,
            response_format={"type": "json_object"}
        )
        
        translated_text = response.choices[0].message.content
        
        # Debug: log first 500 chars of response
        print(f"API Response preview: {translated_text[:500]}...")
        
        # Parse JSON response
        try:
            translated_json = json.loads(translated_text)
            translated_chunk = {}
            
            # Ensure we only include keys that were in the original chunk
            for key, value in translated_json.items():
                if key in strings_chunk:
                    # Check if placeholders were preserved correctly
                    original_placeholders = extract_placeholders(strings_chunk[key])
                    translated_placeholders = extract_placeholders(value)
                    
                    if original_placeholders != translated_placeholders:
                        print(f"Warning: Placeholders modified in '{key}':")
                        print(f"  Original: {original_placeholders}")
                        print(f"  Translated: {translated_placeholders}")
                    
                    translated_chunk[key] = value
                else:
                    print(f"Warning: Unexpected key in response: {key}")
                    
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response was: {translated_text}")
            # Fallback to empty dict on parse error
            translated_chunk = {}
        
        # Check for missing translations and retry once if needed
        missing_keys = set(strings_chunk.keys()) - set(translated_chunk.keys())
        if missing_keys and len(missing_keys) <= 10:  # Only retry if a small number are missing
            print(f"Retrying {len(missing_keys)} missing keys: {list(missing_keys)[:5]}{'...' if len(missing_keys) > 5 else ''}")
            
            # Create a chunk with just the missing keys
            missing_chunk = {key: strings_chunk[key] for key in missing_keys}
            
            # Simplified retry with a more direct prompt
            retry_system_prompt = f"""You are translating iOS app strings from {source_language} to {target_language}.

Return ONLY a JSON object with the exact same keys as the input. Translate ONLY the values.
Keep all iOS placeholders (%@, %d, %lld, etc.) exactly as they are.

Example: {{"key": "Hello %@"}} -> {{"key": "Hola %@"}}"""
            
            retry_user_prompt = f"Translate to {target_language}:\n{json.dumps(missing_chunk, ensure_ascii=False)}"
            
            try:
                retry_response = await client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": retry_system_prompt},
                        {"role": "user", "content": retry_user_prompt}
                    ],
                    temperature=0.3,  # Lower temperature for more consistent output
                    response_format={"type": "json_object"}
                )
                
                retry_text = retry_response.choices[0].message.content
                try:
                    retry_json = json.loads(retry_text)
                    # Add successful retries to the main result
                    for key, value in retry_json.items():
                        if key in missing_keys:
                            translated_chunk[key] = value
                            print(f"Successfully retried key: {key}")
                except json.JSONDecodeError:
                    print(f"Retry failed to parse JSON: {retry_text}")
            except Exception as e:
                print(f"Retry request failed: {e}")
        
        # Final check for still missing keys
        final_missing = set(strings_chunk.keys()) - set(translated_chunk.keys())
        if final_missing:
            print(f"Warning: {len(final_missing)} keys still not translated after retry: {list(final_missing)[:5]}{'...' if len(final_missing) > 5 else ''}")
        
        return translated_chunk
        
    except Exception as e:
        print(f"Warning: Translation failed for chunk: {str(e)}")
        return {}


def translate_strings(
    keys: List[str],
    target_language: str, 
    source_language: str = "en",
    app_description: Optional[str] = None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Translate a dictionary of strings using chunked async processing with openai API.
    
    Args:
        keys (Dict[str, str]): Dictionary of key-value pairs to translate
        target_language (str): Target language code (e.g., 'es', 'fr', 'de')
        source_language (str): Source language code (default: 'en')
        app_description (Optional[str]): Optional description of the app for better translation context
        
    Returns:
        Tuple[Dict[str, str], Dict[str, str]]: Tuple of (translated key-value pairs, skipped keys with reasons)
        
    Raises:
        Exception: If translation fails
    """
    if not keys:
        return {}, {}
    
    # Convert list of keys to dictionary where key=value (for translation purposes)
    keys_dict = {key: key for key in keys}
    
    # If small enough, process as single chunk
    if len(keys_dict) <= settings.translation_chunk_size:
        async def single_chunk_wrapper():
            return await translate_chunk_async(keys_dict, target_language, source_language, app_description)
        
        def run_async_in_thread():
            return asyncio.run(single_chunk_wrapper())
        
        try:
            # Check if we're in an event loop
            asyncio.get_running_loop()
            # We're in an event loop, run in a separate thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                result = future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run directly
            result = asyncio.run(single_chunk_wrapper())
        
        skipped_keys = {k: "Translation not returned by API" for k in keys if k not in result}
        return result, skipped_keys
    
    # Split into chunks for large dictionaries
    items = list(keys_dict.items())
    chunks = []
    
    for i in range(0, len(items), settings.translation_chunk_size):
        chunk_items = items[i:i + settings.translation_chunk_size]
        chunk_dict = dict(chunk_items)
        chunks.append(chunk_dict)
    
    print(f"Processing {len(keys_dict)} strings in {len(chunks)} chunks of max {settings.translation_chunk_size} each...")
    
    async def process_all_chunks():
        """Process all chunks concurrently with limited concurrency and rate limiting."""
        semaphore = asyncio.Semaphore(settings.translation_max_concurrent_chunks)  # Limit concurrent requests for rate limiting
        
        async def process_chunk_with_semaphore(chunk):
            async with semaphore:
                # Add delay between requests to respect rate limits
                await asyncio.sleep(settings.translation_rate_limit_delay)
                return await translate_chunk_async(chunk, target_language, source_language, app_description)
        
        # Process chunks concurrently
        tasks = [process_chunk_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        combined_results = {}
        skipped_keys = {}
        successful_chunks = 0
        
        for i, (chunk, result) in enumerate(zip(chunks, results)):
            if isinstance(result, Exception):
                print(f"Warning: Chunk {i+1} failed: {result}")
                # Mark all keys in this chunk as skipped due to error
                for key in chunk:
                    skipped_keys[key] = f"Chunk {i+1} failed: {str(result)}"
            elif isinstance(result, dict):
                combined_results.update(result)
                successful_chunks += 1
                # Check for missing keys in this chunk
                for key in chunk:
                    if key not in result:
                        skipped_keys[key] = f"Not returned by API in chunk {i+1}"
            
        print(f"Successfully translated {successful_chunks}/{len(chunks)} chunks")
        print(f"Total translations collected: {len(combined_results)} out of {len(keys_dict)} requested")
        print(f"Skipped keys: {len(skipped_keys)}")
        return combined_results, skipped_keys
    
    def run_chunks_in_thread():
        return asyncio.run(process_all_chunks())
    
    try:
        # Check if we're in an event loop
        try:
            asyncio.get_running_loop()
            # We're in an event loop, run in a separate thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_chunks_in_thread)
                return future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run directly
            return asyncio.run(process_all_chunks())
    except Exception as e:
        raise Exception(f"Chunked translation failed: {str(e)}")


def translate_single_key(
    file_path: str,
    key: str,
    target_languages: List[str],
    source_language: str = "en",
    app_description: Optional[str] = None
) -> Tuple[Dict[str, Dict[str, str]], str, Dict[str, str]]:
    """
    Translate a single key to multiple target languages and apply translations to a Localizable.xcstrings file.
    
    Args:
        file_path (str): Path to the .xcstrings file
        key (str): The specific key to translate
        target_languages (List[str]): List of target language codes
        source_language (str): Source language code (default: 'en')
        app_description (Optional[str]): Optional description of the app for better translation context
        
    Returns:
        Tuple[Dict[str, Dict[str, str]], str, Dict[str, str]]: Tuple of (translations by language, backup file path, errors by language)
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        KeyError: If the key doesn't exist in the file
        json.JSONDecodeError: If the file is not valid JSON
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get base language strings (now returns list of keys)
    base_keys = get_base_language_strings(file_path)
    if key not in base_keys:
        raise KeyError(f"Key '{key}' not found in {file_path}")
    
    # For translation, we'll use the key as both key and value
    single_key_dict = {key: key}
    
    # Create backup before modifying the file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.bak.{timestamp}"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path}")
    except Exception as e:
        raise Exception(f"Failed to create backup: {str(e)}")
    
    # Load the xcstrings file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'strings' not in data:
        data['strings'] = {}
    
    # Translate to each target language
    translations_by_language = {}
    errors_by_language = {}
    
    for target_lang in target_languages:
        try:
            # Translate the single key
            translated, skipped = translate_strings(single_key_dict, target_lang, source_language, app_description)
            
            if key in translated:
                # Apply the translation
                if key not in data['strings']:
                    data['strings'][key] = {"localizations": {}}
                
                if 'localizations' not in data['strings'][key]:
                    data['strings'][key]['localizations'] = {}
                
                data['strings'][key]['localizations'][target_lang] = {
                    "stringUnit": {
                        "state": "translated",
                        "value": translated[key]
                    }
                }
                
                translations_by_language[target_lang] = {key: translated[key]}
            else:
                error_msg = skipped.get(key, "Translation failed") if skipped else "Translation failed"
                errors_by_language[target_lang] = error_msg
                
        except Exception as e:
            errors_by_language[target_lang] = str(e)
    
    # Write back to file if we have any successful translations
    if translations_by_language:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Failed to write file: {str(e)}")
    
    return translations_by_language, backup_path, errors_by_language


def apply_missing_translations(
    file_path: str,
    target_language: str,
    source_language: str = "en",
    app_description: Optional[str] = None
) -> Tuple[Dict[str, str], str, str, Dict[str, str]]:
    """
    Translate and apply only missing translations for a target language in a Localizable.xcstrings file.
    Only keys that don't have translations in the target language will be processed.
    
    Args:
        file_path (str): Path to the .xcstrings file
        target_language (str): Target language code
        source_language (str): Source language code (default: 'en')
        app_description (Optional[str]): Optional description of the app for better translation context
        
    Returns:
        Tuple[Dict[str, str], str, str, Dict[str, str]]: Tuple of (translated key-value pairs, backup file path, summary message, skipped keys with reasons)
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
        Exception: If translation or file writing fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Load the xcstrings file to check existing translations
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'strings' not in data:
        data['strings'] = {}
    
    # Get base language strings (now returns list of keys)
    base_keys = get_base_language_strings(file_path)
    if not base_keys:
        return {}, "", f"No base language strings found in {file_path}", {}
    
    # Filter out keys that already have translations in the target language
    missing_keys = []
    existing_translations = {}
    
    for key in base_keys:
        # Check if this key already has a translation in the target language
        if key in data['strings']:
            localizations = data['strings'][key].get('localizations', {})
            if target_language in localizations:
                # Key already has translation in target language
                existing_translations[key] = localizations[target_language].get('stringUnit', {}).get('value', '')
            else:
                # Key missing translation in target language
                missing_keys.append(key)
        else:
            # Key doesn't exist at all, needs translation
            missing_keys.append(key)
    
    total_strings = len(base_keys)
    missing_count = len(missing_keys)
    existing_count = len(existing_translations)
    
    if not missing_keys:
        return {}, "", f"All {total_strings} strings already have {target_language} translations in {file_path}", {}
    
    print(f"Found {existing_count} existing {target_language} translations, {missing_count} missing translations")
    
    # Translate only the missing keys
    translations, skipped_keys = translate_strings(missing_keys, target_language, source_language, app_description)
    if not translations and not skipped_keys:
        return {}, "", f"Translation failed for {target_language}", {}
    
    # Create backup before modifying the file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.bak.{timestamp}"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path}")
    except Exception as e:
        raise Exception(f"Failed to create backup: {str(e)}")
    
    # Apply translations and track successful translations
    applied_translations = {}
    for key, value in translations.items():
        if key not in data['strings']:
            # Create new string entry if it doesn't exist
            data['strings'][key] = {
                "localizations": {}
            }
        
        if 'localizations' not in data['strings'][key]:
            data['strings'][key]['localizations'] = {}
        
        # Add the translation for the target language (only if it was missing)
        data['strings'][key]['localizations'][target_language] = {
            "stringUnit": {
                "state": "translated",
                "value": value
            }
        }
        applied_translations[key] = value
    
    # Write back to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Create summary message
        new_translations_count = len(applied_translations)
        total_translations_now = existing_count + new_translations_count
        
        if new_translations_count == 0:
            summary = f"No new {target_language} translations added to {file_path} (all {missing_count} missing translations failed)"
        elif missing_count == new_translations_count:
            summary = f"{target_language} missing translations added to {file_path} ({new_translations_count} new, {total_translations_now}/{total_strings} total)"
        else:
            summary = f"{target_language} missing translations added to {file_path} ({new_translations_count}/{missing_count} new translations completed, {total_translations_now}/{total_strings} total)"
        
        return applied_translations, backup_path, summary, skipped_keys
    except Exception as e:
        raise Exception(f"Failed to write file: {str(e)}")


def translate_and_apply(
    file_path: str,
    target_language: str,
    source_language: str = "en",
    app_description: Optional[str] = None
) -> Tuple[Dict[str, str], str, str, Dict[str, str]]:
    """
    Translate base language strings and apply translations to a Localizable.xcstrings file.
    
    Args:
        file_path (str): Path to the .xcstrings file
        target_language (str): Target language code
        source_language (str): Source language code (default: 'en')
        app_description (Optional[str]): Optional description of the app for better translation context
        
    Returns:
        Tuple[Dict[str, str], str, str, Dict[str, str]]: Tuple of (translated key-value pairs, backup file path, summary message, skipped keys with reasons)
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
        Exception: If translation or file writing fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get base language strings (now returns list of keys)
    base_keys = get_base_language_strings(file_path)
    if not base_keys:
        return {}, "", f"No base language strings found in {file_path}", {}
    
    total_strings = len(base_keys)
    
    # Translate keys
    translations, skipped_keys = translate_strings(base_keys, target_language, source_language, app_description)
    if not translations and not skipped_keys:
        return {}, "", f"Translation failed for {target_language}", {}
    
    # Create backup before modifying the file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.bak.{timestamp}"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path}")
    except Exception as e:
        raise Exception(f"Failed to create backup: {str(e)}")
    
    # Load the xcstrings file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'strings' not in data:
        data['strings'] = {}
    
    # Apply translations and track successful translations
    applied_translations = {}
    for key, value in translations.items():
        if key not in data['strings']:
            # Create new string entry if it doesn't exist
            data['strings'][key] = {
                "localizations": {}
            }
        
        if 'localizations' not in data['strings'][key]:
            data['strings'][key]['localizations'] = {}
        
        # Add or update the translation for the target language
        data['strings'][key]['localizations'][target_language] = {
            "stringUnit": {
                "state": "translated",
                "value": value
            }
        }
        applied_translations[key] = value
    
    # Write back to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Create summary message
        success_count = len(applied_translations)
        skipped_count = len(skipped_keys)
        success_rate = f"{success_count}/{total_strings}"
        
        if success_count == total_strings:
            summary = f"{target_language} added to {file_path} ({success_count} translations completed)"
        elif skipped_count > 0:
            summary = f"{target_language} added to {file_path} ({success_rate} translations completed, {skipped_count} failed/skipped)"
        else:
            summary = f"{target_language} added to {file_path} ({success_rate} translations completed)"
        
        return applied_translations, backup_path, summary, skipped_keys
    except Exception as e:
        raise Exception(f"Failed to write file: {str(e)}")