from typing import Any

from datapizza.agents.agent import Agent
from datapizza.clients.openai_like import OpenAILikeClient

from core.config import REGOLO_API_KEY
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.kitchen_tools import prepare_dish, serve_dish, update_restaurant_is_open, wait_for_dish


SERVING_SYSTEM_PROMPT = """
You operate only during the serving phase.
You must autonomously verify client intolerances against requested/selected dishes,
prepare safe dishes, serve only safe prepared dishes, and close service with
update_restaurant_is_open(false) when no safe service path exists.
Allowed actions: prepare_dish, serve_dish, update_restaurant_is_open.
Do not use any other tools.
""".strip()


class ServingPipeline:
    def __init__(self) -> None:
        llm_client = OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model="gpt-oss-120b",
            base_url="https://api.regolo.ai/v1",
        )
        self.phase_agent = Agent(
            name="serving_phase_agent",
            client=llm_client,
            system_prompt=SERVING_SYSTEM_PROMPT,
            tools=[prepare_dish, wait_for_dish, serve_dish, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=1,
        )

    def reset_memory(self) -> None:
        llm_client = OpenAILikeClient(
            api_key=REGOLO_API_KEY,
            model="gpt-oss-120b",
            base_url="https://api.regolo.ai/v1",
        )
        self.phase_agent = Agent(
            name="serving_phase_agent",
            client=llm_client,
            system_prompt=SERVING_SYSTEM_PROMPT,
            tools=[prepare_dish, wait_for_dish, serve_dish, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=1,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(task_input=task_input)


serving_pipeline = ServingPipeline()
