import os

_openai_client = None


def _get_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        _openai_client = OpenAI(api_key=api_key) if api_key else None
    return _openai_client
