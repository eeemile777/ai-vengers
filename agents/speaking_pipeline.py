from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.kitchen_tools import update_restaurant_is_open
from tools.market_tools import save_menu, send_message


SPEAKING_SYSTEM_PROMPT = 'You operate only during the speaking phase. Allowed actions: send_message, save_menu, update_restaurant_is_open, and get_restaurant. IMPORTANT: Use the get_restaurant tool to check your status. If your restaurant is currently closed (is_open: false), you MUST use update_restaurant_is_open(true) to open it for the upcoming shift, but ONLY AFTER you have successfully planned your menu. Think step-by-step before executing your tool calls.'


class SpeakingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="speaking_phase_agent",
            client=llm_client,
            system_prompt=SPEAKING_SYSTEM_PROMPT,
            tools=[send_message, save_menu, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
        )

    def flush_agent_memory(self) -> None:
        self.phase_agent = Agent(
            name="speaking_phase_agent",
            client=get_llm_client(),
            system_prompt=SPEAKING_SYSTEM_PROMPT,
            tools=[send_message, save_menu, update_restaurant_is_open, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=0,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(task_input=task_input)


speaking_pipeline = SpeakingPipeline()
