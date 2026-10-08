from fastapi import Request

from app.ai.client import CodysseyClient


def get_ai_client(request: Request) -> CodysseyClient:
    return request.app.state.ai_client
