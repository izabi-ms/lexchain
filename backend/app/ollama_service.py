import requests
import json
from typing import Generator

class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.generate_endpoint = f"{base_url}/api/generate"

    def generate_stream(
        self,
        prompt: str,
        model: str = "mistral",
        stream: bool = True,
        timeout: int = 300
    ) -> Generator[str, None, None]:
        """
        Generate a stream of responses from Ollama's API.

        Args:
            prompt: The input prompt for the model
            model: The model to use (default: mistral)
            stream: Whether to stream the response (default: True)
            timeout: Request timeout in seconds (default: 300)

        Yields:
            str: Chunks of the generated response

        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            with requests.post(
                self.generate_endpoint,
                json=payload,
                headers=headers,
                stream=stream,
                timeout=timeout
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'response' in data:
                                yield data['response']
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}, line: {line}")
                            continue
                        except KeyError:
                            print(f"Unexpected response format: {data}")
                            continue
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            raise

    def generate_document(self, prompt: str) -> str:
        """
        Generate a complete document (non-streaming)
        """
        return "".join(self.generate_stream(prompt, stream=False))
