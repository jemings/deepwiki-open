# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepWiki is an AI-powered documentation generator that creates interactive wikis for GitHub, GitLab, or Bitbucket repositories. It analyzes code structure, generates documentation with Mermaid diagrams, and provides a RAG-powered chat interface for asking questions about repositories.

## Build and Run Commands

### Backend (Python/FastAPI)
```bash
# Install dependencies
python -m pip install poetry==2.0.1 && poetry install -C api

# Start OpenAI relay server (port 8002) - Optional, for proxy environments
python -m api.openai_relay

# Start API server (port 8001)
python -m api.main
```

### Frontend (Next.js)
```bash
# Install dependencies
yarn install

# Start dev server (port 3000)
yarn dev

# Build for production
yarn build

# Lint
yarn lint
```

### Docker
```bash
# Run with docker-compose
docker-compose up

# Build locally
docker build -t deepwiki-open .
```

### Testing
```bash
# Run all tests
python tests/run_tests.py

# Run specific test category
python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --api

# Check environment setup only
python tests/run_tests.py --check-env
```

## Architecture

### Backend (`api/`)
- **api.py**: FastAPI application with REST endpoints for wiki generation, caching, and export
- **websocket_wiki.py**: WebSocket handlers for streaming chat completions and wiki generation
- **openai_relay.py**: Local OpenAI API relay server (optional, for environments with proxy timeouts)
- **rag.py**: RAG (Retrieval Augmented Generation) implementation using AdalFlow and FAISS for code Q&A
- **data_pipeline.py**: Repository cloning, file processing, and embedding generation
- **config.py**: Configuration loading from JSON files and environment variables
- **prompts.py**: System prompts and templates for LLM interactions

### LLM Provider Clients (`api/`)
Multiple provider support with client implementations:
- `openai_client.py`, `openrouter_client.py`, `ollama_patch.py`
- `google_embedder_client.py`, `bedrock_client.py`, `azureai_client.py`, `dashscope_client.py`

### Frontend (`src/`)
- **app/page.tsx**: Main homepage with repository input and generation controls
- **app/[owner]/[repo]/page.tsx**: Wiki view page for generated documentation
- **components/Ask.tsx**: RAG-powered chat interface
- **components/Mermaid.tsx**: Mermaid diagram renderer
- **components/ConfigurationModal.tsx**: Model and configuration selection
- **contexts/LanguageContext.tsx**: i18n support

### Configuration (`api/config/`)
- **generator.json**: LLM provider and model configurations
- **embedder.json**: Embedding model settings for vector storage
- **repo.json**: Repository file filters and processing rules
- **lang.json**: Supported languages for wiki generation

## Key Environment Variables

Required (at least one):
- `GOOGLE_API_KEY`: For Gemini models and Google embeddings
- `OPENAI_API_KEY`: For OpenAI models and embeddings

Optional providers:
- `OPENROUTER_API_KEY`: OpenRouter models
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_VERSION`: Azure OpenAI
- `OLLAMA_HOST`: Custom Ollama server (default: http://localhost:11434)
- AWS credentials for Bedrock: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

Configuration:
- `DEEPWIKI_EMBEDDER_TYPE`: `openai` (default), `google`, `ollama`, or `bedrock`
- `DEEPWIKI_CONFIG_DIR`: Custom config directory path
- `DEEPWIKI_DEFAULT_PROVIDER`: Override default LLM provider from generator.json
- `PORT`: API server port (default: 8001)
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `DEEPWIKI_AUTH_MODE`, `DEEPWIKI_AUTH_CODE`: Optional authorization for wiki generation

## Optional: OpenAI Relay Server

For environments with restrictive proxy settings that may timeout long-running API requests, you can use the included relay server:

1. Set `OPENAI_BASE_URL=http://localhost:8002/v1` in `.env`
2. Start relay server before backend: `python -m api.openai_relay`

The relay server:
- Maintains streaming connections to prevent proxy timeouts
- Automatically retries failed requests
- Creates fresh client connections to avoid stale connection issues

**Note**: If you're developing in a corporate proxy environment with specific requirements, check `~/.claude/projects/` for environment-specific configuration. For Claude Code users, the project-specific CLAUDE.md (if present) will be automatically loaded alongside this file.

## Data Storage

AdalFlow stores data in `~/.adalflow/`:
- `repos/`: Cloned repositories
- `databases/`: Embeddings and FAISS indexes
- `wikicache/`: Generated wiki content cache

## Development Notes

- **Check TODO.md** for pending tasks, improvements, and known issues
- Performance baselines and optimization targets are documented in TODO.md
