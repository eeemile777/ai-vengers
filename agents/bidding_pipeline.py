from typing import Any

from datapizza.agents.agent import Agent

from core.client import get_llm_client
from tools.market_tools import closed_bid


BIDDING_SYSTEM_PROMPT = """You are the procurement engine for the closed_bid phase. Your objective is zero-waste ingredient acquisition.
CRITICAL RULES:
1. INGREDIENTS EXPIRE: All ingredients expire at the end of this turn. NEVER hoard. Buy exactly what you need.
2. SINGLE BID OVERRIDE: Submitting multiple bids overwrites the previous one. You must calculate your ENTIRE bid list and submit it in a SINGLE `closed_bid` tool call.
3. CALCULATION ALGORITHM:
   - The restaurant state (balance and inventory) and recipes are already provided in this task — do NOT call any lookup tools.
   - Identify the dishes on your planned menu.
   - Calculate the total quantity of each ingredient required.
   - Subtract your current inventory from the task context.
   - The result is your target purchase list.
   - Submit exactly ONE `closed_bid` with an aggressive but efficient price for these missing ingredients.
4. STOP RULE: If `closed_bid` returns "retriable": false, do NOT retry. Terminate your sequence immediately."""


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