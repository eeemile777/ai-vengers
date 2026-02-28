from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.kitchen_tools import update_restaurant_is_open
from tools.market_tools import save_menu, send_message


SPEAKING_SYSTEM_PROMPT = """You operate only during the speaking phase.
CRITICAL MENU RULE:
You currently have NO INVENTORY because ingredients expire every turn.
1. Choose a target demographic for this turn (e.g., Astrobarons for high margins, or Explorers for volume).
2. Call `get_recipes()` and select 1 or 2 dishes that fit this strategy and are realistic to acquire.
3. Call `save_menu` with these dishes and appropriate prices (high for Astrobarons, low for volume).
4. This menu dictates what you will attempt to buy in the upcoming `closed_bid` phase. Do not overcomplicate it.
DIPLOMACY: Optionally use `send_message` to contact other teams for cartel coordination or misdirection.
STATUS: Call `get_restaurant` to verify the restaurant is open (`is_open: true`). If closed, call `update_restaurant_is_open({"is_open": true})`."""


class SpeakingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="speaking_phase_agent",
            client=llm_client,
            system_prompt=SPEAKING_SYSTEM_PROMPT,
            tools=[send_message, save_menu, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
            max_steps=15,
        )

    def flush_agent_memory(self) -> None:
        self.phase_agent = Agent(
            name="speaking_phase_agent",
            client=get_llm_client(),
            system_prompt=SPEAKING_SYSTEM_PROMPT,
            tools=[send_message, save_menu, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
            max_steps=15,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(task_input=task_input)


speaking_pipeline = SpeakingPipeline()
