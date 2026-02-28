from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.kitchen_tools import prepare_dish, serve_dish, update_restaurant_is_open, wait_for_dish


SERVING_SYSTEM_PROMPT = """You are the autonomous execution engine for the serving phase. Your ONLY goal is safely serving clients and protecting the restaurant's reputation.
CRITICAL RULES:
1. LETHAL INTOLERANCES: You MUST check the 'intolerances' field for every client before cooking. Serving a dish containing an intolerant ingredient causes catastrophic failure.
2. EXECUTION ALGORITHM: For EVERY client that spawns:
   - Call `get_meals()` to find their specific `client_id` and order text.
   - Cross-reference their intolerances with `get_recipes()`.
   - Call `prepare_dish({"dish_name": "<safe_dish>"})`.
   - Call `wait_for_dish({"client_id": "<id>", "dish_name": "<safe_dish>"})` to synchronize the SSE completion event.
   - Call `serve_dish({"dish_name": "<safe_dish>", "client_id": "<id>"})`.
3. PANIC BUTTON: If you lack the ingredients to cook a safe dish, or if you are overwhelmed by volume, you MUST call `update_restaurant_is_open({"is_open": false})` immediately to protect our reputation. Do NOT hallucinate ingredients you do not have.
Think step-by-step and strictly follow the execution algorithm."""


class ServingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="serving_phase_agent",
            client=llm_client,
            system_prompt=SERVING_SYSTEM_PROMPT,
            tools=[prepare_dish, wait_for_dish, serve_dish, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
            max_steps=15,
        )

    def flush_agent_memory(self) -> None:
        self.phase_agent = Agent(
            name="serving_phase_agent",
            client=get_llm_client(),
            system_prompt=SERVING_SYSTEM_PROMPT,
            tools=[prepare_dish, wait_for_dish, serve_dish, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
            max_steps=15,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(task_input=task_input)


serving_pipeline = ServingPipeline()
