from datapizza.clients.openai_like import OpenAILikeClient

from core.config import REGOLO_API_KEY


def get_llm_client() -> OpenAILikeClient:
    return OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model="gpt-oss-120b",
        base_url="https://api.regolo.ai/v1",
    )