"""
LLM Client for llama-server
Handles communication with local llama-server instance
"""

import requests
from typing import List, Dict, Optional
from loguru import logger


class LlamaServerClient:
    """Client for interacting with llama-server"""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        timeout: int = 120,
    ):
        """
        Initialize llama-server client

        Args:
            base_url: Base URL of llama-server
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        logger.info(f"Initialized LlamaServerClient for {base_url}")

    def health_check(self) -> bool:
        """Check if server is healthy"""
        try:
            response = requests.get(
                f"{self.base_url}/health", headers=self.headers, timeout=5
            )
            is_healthy = response.status_code == 200
            logger.info(f"Health check: {'OK' if is_healthy else 'FAILED'}")
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        stream: bool = False,
    ) -> Dict:
        """
        OpenAI-compatible chat completion

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Nucleus sampling threshold
            stop: List of stop sequences
            stream: Whether to stream the response

        Returns:
            Response dict with generated content
        """
        try:
            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "stream": stream,
            }

            if stop:
                payload["stop"] = stop

            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()
            result = response.json()

            logger.debug(f"Chat completion successful ({len(messages)} messages)")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Chat completion failed: {e}")
            raise

    def completion(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
    ) -> Dict:
        """
        Native completion endpoint

        Args:
            prompt: Text prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            stop: List of stop sequences

        Returns:
            Response dict with generated content
        """
        try:
            payload = {
                "prompt": prompt,
                "n_predict": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
            }

            if stop:
                payload["stop"] = stop

            response = requests.post(
                f"{self.base_url}/completion",
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()
            result = response.json()

            logger.debug(f"Completion successful (prompt length: {len(prompt)})")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Completion failed: {e}")
            raise

    def generate_with_context(
        self,
        query: str,
        context: str,
        system_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate response with RAG context

        Args:
            query: User query
            context: Retrieved context from RAG
            system_prompt: System instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated response text
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Konteks dari buku:\n{context}\n\nPertanyaan: {query}",
            },
        ]

        result = self.chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=temperature
        )

        # Extract content from response
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0].get("message", {})
            content = message.get("content", "")
            return content
        else:
            logger.warning("No content in response")
            return ""


if __name__ == "__main__":
    # Test the client
    import os
    from dotenv import load_dotenv

    load_dotenv()

    client = LlamaServerClient(
        base_url=os.getenv("LLAMA_SERVER_URL", "http://localhost:8080"),
        api_key=os.getenv("LLAMA_API_KEY"),
    )

    # Health check
    if client.health_check():
        print("✓ Server is healthy")

        # Test chat completion
        print("\n=== Testing Chat Completion ===")
        response = client.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "Kamu adalah guru STEM untuk siswa SMP Indonesia.",
                },
                {"role": "user", "content": "Apa itu percepatan?"},
            ],
            max_tokens=256,
        )

        if "choices" in response:
            content = response["choices"][0]["message"]["content"]
            print(f"Response: {content}")
        else:
            print("No response content")

    else:
        print("✗ Server is not healthy. Make sure llama-server is running.")
