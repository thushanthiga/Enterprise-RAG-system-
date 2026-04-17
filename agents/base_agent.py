"""
BaseAgent — foundation class for all agents.
Provides call_llm() for single-shot and stream_llm() for streaming.
Temperature is always low (0.0–0.2) to keep outputs deterministic.
"""
from __future__ import annotations

import json
import re
import asyncio
from typing import AsyncGenerator, Optional

import httpx

from pathlib import Path
from config import OLLAMA_URL, OLLAMA_MODEL

SETTINGS_DATA = Path(__file__).parent.parent / "data" / "settings.json"

class BaseAgent:
    """Base class that all agents inherit from.
    Handles all Ollama communication so sub-agents only define prompts."""

    def __init__(self, model: Optional[str] = None, temperature: float = 0.0, settings: Optional[dict] = None):
        # Use provided settings or fallback to defaults
        s = settings or {}
        
        # Fallback to JSON if not provided (for standalone scripts or transition)
        if not s and SETTINGS_DATA.exists():
            try:
                with open(SETTINGS_DATA) as f:
                    s = json.load(f)
            except:
                pass
        
        self.provider = s.get("active_llm_provider", "ollama")
        self.temperature = temperature
        
        # Initial model/url mapping
        self.ollama_url = s.get("ollama_url", OLLAMA_URL)
        self.ollama_model = model or s.get("ollama_model", OLLAMA_MODEL)
        self.base_url = self.ollama_url # for backward compat in _post_with_retry
        
        # Providers Model Names
        self.openai_model = s.get("openai_model", "gpt-4-turbo-preview")
        self.anthropic_model = s.get("anthropic_model", "claude-3-5-sonnet-20240620")
        self.google_model_name = s.get("gemini_model", "gemini-1.5-pro")
        
        # Clients for various providers
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_client = None
        
        self._init_clients(s)

    def _init_clients(self, s: dict):
        # OpenAI / DeepSeek / Grok
        api_key = s.get("openai_api_key")
        base_url = None
        
        if self.provider == "deepseek":
            api_key = s.get("deepseek_api_key")
            base_url = "https://api.deepseek.com"
            self.openai_model = s.get("deepseek_model", "deepseek-chat")
        elif self.provider == "grok":
            api_key = s.get("grok_api_key")
            base_url = "https://api.x.ai/v1"
            self.openai_model = s.get("grok_model", "grok-1")

        if api_key:
            from openai import AsyncOpenAI
            self.openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        # Anthropic
        if s.get("anthropic_api_key"):
            from anthropic import AsyncAnthropic
            self.anthropic_client = AsyncAnthropic(api_key=s["anthropic_api_key"])
            
        # Google
        if s.get("gemini_api_key"):
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=s["gemini_api_key"])
            except ImportError:
                pass

    # ── Single-shot LLM call ─────────────────────────────────────────
    async def call_llm(
        self,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Send a prompt and return the full response text."""
        temp = temperature if temperature is not None else self.temperature

        # 1. OpenAI / DeepSeek / Grok
        if self.provider in ["openai", "deepseek", "grok"] and self.openai_client:
            try:
                messages = [{"role": "system", "content": system}]
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": user})

                resp = await self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    temperature=temp,
                    stream=False
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                return f"{self.provider.upper()} Error: {str(e)}"

        # 2. Anthropic
        if self.provider == "anthropic" and self.anthropic_client:
            try:
                messages = []
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": user})

                resp = await self.anthropic_client.messages.create(
                    model=self.anthropic_model,
                    max_tokens=4096,
                    system=system,
                    messages=messages,
                    temperature=temp
                )
                return resp.content[0].text
            except Exception as e:
                return f"Anthropic Error: {str(e)}"

        # 3. Google Gemini
        if self.provider == "gemini" and self.gemini_client:
            try:
                from google.genai import types
                history_text = ""
                if history:
                    for h in history:
                        role = "User" if h["role"] == "user" else "AI"
                        history_text += f"{role}: {h['content']}\n"
                
                full_contents = f"System Instruction: {system}\n\n{history_text}User Question: {user}"
                resp = await self.gemini_client.aio.models.generate_content(
                    model=self.google_model_name,
                    contents=full_contents,
                    config=types.GenerateContentConfig(temperature=temp)
                )
                return resp.text
            except Exception as e:
                return f"Gemini Error: {str(e)}"

        # Default to Ollama (using /api/chat for history support)
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})

        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temp},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await self._post_with_retry(client, "/api/chat", payload)
            return resp.get("message", {}).get("content", "")

    # ── Streaming LLM call ───────────────────────────────────────────
    async def stream_llm(
        self,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        history: Optional[list[dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from any provider one-by-one."""
        temp = temperature if temperature is not None else self.temperature

        # 1. OpenAI / DeepSeek / Grok
        if self.provider in ["openai", "deepseek", "grok"] and self.openai_client:
            try:
                messages = [{"role": "system", "content": system}]
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": user})

                stream = await self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages,
                    temperature=temp,
                    stream=True
                )
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                yield f"{self.provider.upper()} Stream Error: {str(e)}"
                return

        # 2. Anthropic
        if self.provider == "anthropic" and self.anthropic_client:
            try:
                messages = []
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": user})

                async with self.anthropic_client.messages.stream(
                    model=self.anthropic_model,
                    max_tokens=4096,
                    system=system,
                    messages=messages,
                    temperature=temp
                ) as stream:
                    async for text in stream.text_stream:
                        yield text
                return
            except Exception as e:
                yield f"Anthropic Stream Error: {str(e)}"
                return

        # 3. Google Gemini
        if self.provider == "gemini" and self.gemini_client:
            try:
                from google.genai import types
                history_text = ""
                if history:
                    for h in history:
                        role = "User" if h["role"] == "user" else "AI"
                        history_text += f"{role}: {h['content']}\n"
                
                full_contents = f"System Instruction: {system}\n\n{history_text}User Question: {user}"
                resp = await self.gemini_client.aio.models.generate_content_stream(
                    model=self.google_model_name,
                    contents=full_contents,
                    config=types.GenerateContentConfig(temperature=temp)
                )
                async for chunk in resp:
                    yield chunk.text
                return
            except Exception as e:
                yield f"Gemini Stream Error: {str(e)}"
                return

        # Default to Ollama
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})

        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temp},
        }
        url = f"{self.ollama_url}/api/chat"
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break

    # ── Retry wrapper ────────────────────────────────────────────────
    async def _post_with_retry(
        self, client: httpx.AsyncClient, path: str, payload: dict, retries: int = 3
    ) -> dict:
        url = f"{self.base_url}{path}"
        for attempt in range(retries):
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return {}

    # ── JSON parsing helper ──────────────────────────────────────────
    @staticmethod
    def parse_llm_json(raw: str) -> dict:
        """Parse JSON that may be wrapped in markdown fences."""
        clean = re.sub(r"```json|```", "", raw).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"No valid JSON in LLM output: {raw[:120]}")
