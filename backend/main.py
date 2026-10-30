"""
TestGen AI — FastAPI Backend
Powered by NVIDIA Nemotron on Nebius AI Cloud
"""

import asyncio
import json
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from agent import TestGenAgent

load_dotenv()

app = FastAPI(
    title="TestGen AI API",
    description="AI-powered test generation using NVIDIA Nemotron on Nebius AI Cloud",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    code: str
    language: str = "python"
    filename: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "TestGen AI",
        "powered_by": "NVIDIA Nemotron on Nebius AI Cloud",
    }


@app.post("/api/generate")
async def generate_tests(request: GenerateRequest):
    """
    Full pipeline: analyze code → generate tests → run → fix → return results.
    Returns the complete result as JSON (no streaming).
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    if len(request.code) > 50_000:
        raise HTTPException(status_code=400, detail="Code too large (max 50KB).")
    if request.language not in ("python",):
        raise HTTPException(status_code=400, detail="Unsupported language. Supported: python")

    agent = TestGenAgent()
    result = await agent.run(request.code, request.language)
    return result


@app.post("/api/stream")
async def stream_generate_tests(request: GenerateRequest):
    """
    Streaming pipeline using Server-Sent Events (SSE).
    Yields real-time step updates as the agent works.
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    if len(request.code) > 50_000:
        raise HTTPException(status_code=400, detail="Code too large (max 50KB).")
    if request.language not in ("python",):
        raise HTTPException(status_code=400, detail="Unsupported language. Supported: python")

    async def event_generator():
        agent = TestGenAgent()
        try:
            async for event in agent.run_streaming(request.code, request.language):
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)  # yield control to event loop
        except Exception as e:
            error_payload = json.dumps({"event": "error", "data": {"message": str(e)}})
            yield f"data: {error_payload}\n\n"
        finally:
            yield "data: {\"event\": \"done\", \"data\": {}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/")
async def root():
    return {
        "name": "TestGen AI",
        "tagline": "AI-powered unit test generation with NVIDIA Nemotron",
        "endpoints": {
            "POST /api/generate": "Generate tests (blocking)",
            "POST /api/stream": "Generate tests with SSE streaming",
            "GET /health": "Health check",
        }
    }
