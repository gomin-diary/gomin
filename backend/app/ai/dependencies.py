from fastapi import Request

from app.ai.client import CodysseyClient, GeminiClient


def get_ai_client(request: Request) -> CodysseyClient:
    return request.app.state.ai_client


def get_image_ai_client(request: Request) -> GeminiClient:
    return request.app.state.image_ai_client
