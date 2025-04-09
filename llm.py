from mistralai import Mistral
from openai import OpenAI
import os

class LLM: 

    def __init__(self, model_name: str, provider: str):
        self.model_name = model_name
        self.provider = provider

        if self.provider == "mistral":
            self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        elif self.provider == "vllm":
            self.client = OpenAI(base_url="http://localhost:8000/v1", api_key=os.getenv("VLLM_API_KEY"))
        

    def generate_text(self, prompt: str, response_format: str = None):

        if self.provider == "mistral":
            response = self.client.chat.complete(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format=response_format
            )
            return response.choices[0].message.content
        elif self.provider == "vllm":
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        else:
            raise ValueError(f"Provider {self.provider} not supported")
    