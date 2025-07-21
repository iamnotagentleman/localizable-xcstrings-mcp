# Localizable XStrings MCP Server

A Model Context Protocol (MCP) server that provides tools for working with iOS Localizable.xcstrings files. This tool enables automated translation workflows and localization management for iOS/macOS projects using Xcode String Catalogs.

## Features

- **Extract Language Support**: Get all supported language codes from .xcstrings files
- **Key Management**: Extract all localization keys and base language strings
- **Automated Translation**: Translate strings using OpenAI API
- **Batch Processing**: Chunked translation (50 strings per chunk) with async concurrency
- **File Management**: Apply translations back to .xcstrings files while preserving structure
- **Cost-Effective**: Uses OpenAI API for translations

## Setup

### Prerequisites

- Python 3.12+
- uv (Python package manager)
- OpenAI API key (for translation features)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd localizable-xcstrings-mcp
```

2. Install dependencies with uv:
```bash
uv sync
```

### Configuration

1. **Get an OpenAI API key** from [platform.openai.com](https://platform.openai.com/api-keys)

2. **Create a .env file** and add your OpenAI API key:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Optional**: Customize other settings in the .env file:
   - `OPENAI_MODEL`: Choose the translation model (default: gpt-4o-mini)
   - `TRANSLATION_CHUNK_SIZE`: Adjust batch size for large files
   - `TRANSLATION_TEMPERATURE`: Control translation creativity (0.0-1.0)
   - `TRANSLATION_MAX_CONCURRENT_CHUNKS`: Limit concurrent API requests
   - `TRANSLATION_RATE_LIMIT_DELAY`: Delay between API calls

## Usage

### Running the MCP Server

Start the server with:
```bash
uv run src/localizable_xstrings_mcp/server.py 
```

This will launch a FastMCP interface where you can:
- Upload .xcstrings files
- Extract language information and keys
- Translate strings to target languages
- Apply translations back to files

### Available Tools

1. **Get Languages**: Extract supported language codes from .xcstrings files
2. **Get Keys**: List all localization keys
3. **Get Base Strings**: Extract base language key-value pairs
4. **Translate**: Preview translations using OpenAI API
5. **Apply Translations**: Translate and apply to .xcstrings files
6. **Apply Missing**: Translate and apply only missing translations for a target language
7. **Translate Key**: Translate specific keys to multiple languages

## Adding to Claude Code

To use this MCP server with Claude Code, follow these steps:

### 1. Install and Configure

First, ensure the package is installed in your Python environment:
```bash
uv sync
```

### 2. Add to Claude Code

Use the fastmcp install command:
```bash
fastmcp install claude-code server.py --name "localizable-xcstrings" \
  --env OPENAI_API_KEY=your-api-key \
  --env OPENAI_MODEL=gpt-4o-mini
```

### 3. Restart Claude Code

After installation, restart Claude Code to load the new MCP server.

### 4. Verify Installation

In Claude Code, you should now have access to these tools:
- `get_languages_tool`
- `get_keys_tool` 
- `get_base_strings_tool`
- `translate_tool`
- `apply_tool`
- `apply_missing_tool`
- `translate_key_tool`

## Example Workflow

1. **Extract information from your .xcstrings file**:
   ```
   Use get_languages_tool with path to your Localizable.xcstrings file
   ```

2. **Get all localization keys**:
   ```
   Use get_keys_tool to see all string identifiers
   ```

3. **Translate to a new language**:
   ```
   Use apply_tool with target language (e.g., "de" for German)
   Ensure your .env file is properly configured with your OpenAI API key
   ```

4. **Translate specific keys**:
   ```
   Use translate_key_tool for individual string translations
   ```

## Environment Variables

All configuration is managed through environment variables in the `.env` file:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | Your OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model for translations |
| `OPENAI_BASE_URL` | No | - | Custom API base URL |
| `TRANSLATION_CHUNK_SIZE` | No | `50` | Strings per API request |
| `TRANSLATION_TEMPERATURE` | No | `0.3` | Model creativity (0.0-1.0) |
| `TRANSLATION_MAX_CONCURRENT_CHUNKS` | No | `2` | Max concurrent requests |
| `TRANSLATION_RATE_LIMIT_DELAY` | No | `1.0` | Delay between requests (seconds) |

## File Format Support

This tool works with Xcode 15+ String Catalog files (.xcstrings). These files use a JSON structure to store localized strings and metadata.

## Translation Features

- **Chunked Processing**: Large translation jobs are split into 50-string chunks
- **Async Concurrency**: Up to 3 chunks processed simultaneously
- **Token Limit Protection**: Prevents API context limit issues
- **Progress Reporting**: Shows processing status for large jobs
- **Cost-Effective**: Uses OpenAI API for translations

## Testing

Run the test suite:
```bash
uv run pytest tests/test_xcstrings_tools.py -v
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Support

For issues and questions:
- Check the test files for usage examples
- Open an issue on the repository