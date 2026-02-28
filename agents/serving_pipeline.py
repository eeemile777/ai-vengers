from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.kitchen_tools import prepare_dish, serve_dish, update_restaurant_is_open, wait_for_dish


SERVING_SYSTEM_PROMPT = 'You operate only during the serving phase. The real-time client events do NOT contain the client_id needed for serving. You MUST use the get_meals tool to fetch the active client orders and their corresponding client_ids. Match the clients, prepare safe dishes using prepare_dish, immediately use wait_for_dish, and finally use serve_dish.'


class ServingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
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
