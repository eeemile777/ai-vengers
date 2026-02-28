import logging
from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals, get_client_id_for_order
from tools.kitchen_tools import check_safety, prepare_dish, serve_dish, update_restaurant_is_open, wait_for_dish

logger = logging.getLogger(__name__)

SERVING_SYSTEM_PROMPT = """You are the autonomous execution engine for the serving phase. Your ONLY goal is safely serving clients and protecting the restaurant's reputation.
CRITICAL RULES:
1. EXECUTION ALGORITHM: For EVERY client task you receive:
   - Call `get_client_id_for_order({"client_name": "<name>"})` to get their exact client_id. Never guess or fabricate a client_id.
   - Call `check_safety({"client_intolerances": [...], "dish_name": "<dish>"})` for each candidate dish. The intolerances are provided in your task context.
   - Only proceed with a dish where `is_safe` is true.
   - Call `prepare_dish({"dish_name": "<safe_dish>"})`.
   - ERROR HANDLING: If `prepare_dish` returns an error (missing ingredients, server rejection), DO NOT call `wait_for_dish`. Try a different safe dish or trigger the panic button.
   - Call `wait_for_dish({"client_id": "<id>", "dish_name": "<safe_dish>"})` only after a successful `prepare_dish`.
   - Call `serve_dish({"dish_name": "<safe_dish>", "client_id": "<id>"})`.
2. PANIC BUTTON: If you cannot find any safe and cookable dish for a client, call `update_restaurant_is_open({"is_open": false})` immediately. If you call this, you MUST immediately stop all tool calls and terminate your execution. Do not attempt to serve any remaining clients.
Think step-by-step and strictly follow the execution algorithm."""


class ServingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="serving_phase_agent",
            client=llm_client,
            system_prompt=SERVING_SYSTEM_PROMPT,
            tools=[check_safety, get_client_id_for_order, prepare_dish, wait_for_dish, serve_dish, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_recipes, get_meals],
            planning_interval=0,
            max_steps=15,
        )

    def flush_agent_memory(self) -> None:
        self.phase_agent = Agent(
            name="serving_phase_agent",
            client=get_llm_client(),
            system_prompt=SERVING_SYSTEM_PROMPT,
            tools=[check_safety, get_client_id_for_order, prepare_dish, wait_for_dish, serve_dish, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_recipes, get_meals],
            planning_interval=0,
            max_steps=15,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(
            task_input=task_input,
            tool_choice="auto",
        )


serving_pipeline = ServingPipeline()
