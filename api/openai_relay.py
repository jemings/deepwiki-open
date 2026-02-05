"""
Local OpenAI API relay server.

Solves Samsung proxy idle timeout by:
1. App connects to localhost (no proxy)
2. Relay forwards to OpenAI using streaming (keeps proxy connection alive)
3. Relay assembles full response and returns it to app

Usage:
    python -m api.openai_relay

Then set OPENAI_BASE_URL=http://localhost:8002/v1 in .env
"""

import asyncio
import json
import logging
import os
import time

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import uvicorn
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = "https://api.openai.com/v1"
SSL_CERT = os.environ.get("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")

app = FastAPI()

RELAY_RETRIES = 3
RELAY_RETRY_DELAY = 10  # seconds between relay-level retries


def _create_client():
    """Create a fresh OpenAI client with no stale connections."""
    return OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        max_retries=3,
        http_client=httpx.Client(
            timeout=httpx.Timeout(300.0, connect=30.0),
            verify=SSL_CERT,
        ),
    )


def _call_and_collect(stream_body):
    """Create fresh client, call OpenAI with streaming, collect all chunks."""
    client = _create_client()
    try:
        stream_resp = client.chat.completions.create(**stream_body)

        chunks = []
        completion_id = ""
        model_name = ""
        created_ts = 0
        usage_data = None

        for chunk in stream_resp:
            completion_id = chunk.id or completion_id
            model_name = chunk.model or model_name
            created_ts = chunk.created or created_ts
            if hasattr(chunk, 'usage') and chunk.usage:
                usage_data = chunk.usage
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    chunks.append(delta.content)

        return "".join(chunks), completion_id, model_name, created_ts, usage_data
    finally:
        client.close()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def relay(path: str, request: Request):
    """Relay requests to OpenAI, using streaming internally to survive proxy."""

    # Pass through non-chat-completions requests directly
    if path != "v1/chat/completions":
        async with httpx.AsyncClient(timeout=60.0, verify=SSL_CERT) as http:
            resp = await http.request(
                method=request.method,
                url=f"https://api.openai.com/{path}",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                         "Content-Type": "application/json"},
                content=await request.body(),
            )
            return JSONResponse(content=resp.json(), status_code=resp.status_code)

    body = await request.json()
    want_stream = body.get("stream", False)

    # Always use streaming internally to keep proxy connection alive
    stream_body = {**body, "stream": True}

    start = time.time()
    logger.info(f"Relaying: model={body.get('model')}, stream={want_stream}")

    # Relay-level retry with delays (each attempt creates a fresh connection)
    last_error = None
    for attempt in range(RELAY_RETRIES):
        try:
            result = await asyncio.to_thread(_call_and_collect, stream_body)
            full_content, completion_id, model_name, created_ts, usage_data = result

            elapsed = time.time() - start
            logger.info(f"OK in {elapsed:.1f}s, {len(full_content)} chars (attempt {attempt + 1}/{RELAY_RETRIES})")

            if want_stream:
                # Re-stream collected content as SSE over localhost
                def generate():
                    chunk_size = 20
                    for i in range(0, len(full_content), chunk_size):
                        text = full_content[i:i + chunk_size]
                        sse_chunk = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": model_name,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": text},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(sse_chunk)}\n\n"
                    final_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                return StreamingResponse(generate(), media_type="text/event-stream")
            else:
                response = {
                    "id": completion_id,
                    "object": "chat.completion",
                    "created": created_ts,
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": full_content},
                        "finish_reason": "stop"
                    }],
                }
                if usage_data:
                    response["usage"] = {
                        "prompt_tokens": getattr(usage_data, 'prompt_tokens', 0),
                        "completion_tokens": getattr(usage_data, 'completion_tokens', 0),
                        "total_tokens": getattr(usage_data, 'total_tokens', 0),
                    }
                return JSONResponse(content=response)

        except Exception as e:
            last_error = e
            elapsed = time.time() - start
            if attempt < RELAY_RETRIES - 1:
                logger.warning(
                    f"Attempt {attempt + 1}/{RELAY_RETRIES} failed ({elapsed:.1f}s): "
                    f"{type(e).__name__}: {e}. Retry in {RELAY_RETRY_DELAY}s..."
                )
                await asyncio.sleep(RELAY_RETRY_DELAY)
            else:
                logger.error(
                    f"All {RELAY_RETRIES} attempts failed ({elapsed:.1f}s): "
                    f"{type(e).__name__}: {e}"
                )

    return JSONResponse(
        content={"error": {"message": str(last_error), "type": "relay_error"}},
        status_code=502
    )


if __name__ == "__main__":
    port = int(os.environ.get("RELAY_PORT", 8002))
    logger.info(f"Starting OpenAI relay on port {port}")
    uvicorn.run(app, host="127.0.0.1", port=port)
