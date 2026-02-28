from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.market_tools import closed_bid


BIDDING_SYSTEM_PROMPT = """
You operate only during the closed_bid phase.
Allowed action: submit exactly one closed_bid payload.
Do not attempt any other action or tool.
""".strip()


class BiddingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="bidding_phase_agent",
            client=llm_client,
            system_prompt=BIDDING_SYSTEM_PROMPT,
            tools=[closed_bid, get_restaurant, get_restaurant_menu, get_market_entries, get_recipes, get_meals],
            planning_interval=1,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(
            task_input=task_input,
            tool_choice="auto",
        )


bidding_pipeline = BiddingPipeline()