from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.market_tools import closed_bid


BIDDING_SYSTEM_PROMPT = 'You operate only during the closed_bid phase. The restaurant state and recipes are already provided in the task. Using ONLY that data, calculate which ingredients you are missing, then submit exactly one closed_bid with all required ingredients grouped into a single payload. Do NOT call any lookup tools. WARNING: Submitting multiple bids overwrites previous ones — one call only. STOP RULE: If closed_bid returns "retriable": false, do NOT retry. Accept the result and end your turn immediately. Think step-by-step before executing your tool calls.'


class BiddingPipeline:
    def __init__(self) -> None:
        llm_client = get_llm_client()
        self.phase_agent = Agent(
            name="bidding_phase_agent",
            client=llm_client,
            system_prompt=BIDDING_SYSTEM_PROMPT,
            tools=[closed_bid],
            planning_interval=0,
            max_steps=5,
        )

    def flush_agent_memory(self) -> None:
        self.phase_agent = Agent(
            name="bidding_phase_agent",
            client=get_llm_client(),
            system_prompt=BIDDING_SYSTEM_PROMPT,
            tools=[closed_bid],
            planning_interval=0,
            max_steps=5,
        )

    async def a_run(self, task_input: str) -> Any:
        return await self.phase_agent.a_run(
            task_input=task_input,
            tool_choice="auto",
        )


bidding_pipeline = BiddingPipeline()