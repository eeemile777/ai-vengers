import logging
from typing import Any

from datapizza.agents.agent import Agent
from pydantic import BaseModel, ValidationError

from core.client import get_llm_client
from tools.info_tools import get_market_entries, get_restaurant, get_restaurant_menu, get_recipes, get_meals
from tools.kitchen_tools import update_restaurant_is_open
from tools.market_tools import save_menu, send_message

logger = logging.getLogger(__name__)

SPEAKING_SYSTEM_PROMPT = """
You are the Executive Chef and General Manager of a galactic restaurant operating in the speaking phase. Your objective is to initialize the restaurant for the upcoming turn, define the menu strategy, and calculate the exact ingredient requirements for the bidding team.

### EXECUTION DIRECTIVE (STRICT ORDER):
1. Use the update_restaurant_is_open tool with {"is_open": true} to ensure your restaurant is open for business.
2. Use the get_recipes tool to retrieve the complete catalog of available dishes.
3. Analyze the recipes and select exactly 10 dishes based on their prestige: 
   - 3 high prestige dishes
   - 3 medium prestige dishes
   - 4 low prestige dishes
4. Use the save_menu tool to publish these 10 dishes as your initial menu. Price them strategically based on their prestige.
5. Terminate your execution by outputting a clear, formatted JSON list of all unique ingredients required to cook these 10 recipes. Do not output anything else in your final response except this list, as it will be programmatically passed to the bidding agent.

### CRITICAL RULES:
- Do NOT attempt to use the send_message tool. You are on a strict communications blackout.
- You must complete all tool executions before ending your turn.
"""


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

    async def a_run(
        self,
        task_input: str,
        response_format: type[BaseModel] | None = None,
    ) -> Any:
        result = await self.phase_agent.a_run(task_input=task_input, tool_choice="auto")

        if response_format is not None and result is not None:
            from datapizza.core.clients.models import StructuredBlock

            for block in result.content:
                if isinstance(block, StructuredBlock) and isinstance(block.content, response_format):
                    return block.content

            if result.text:
                try:
                    return response_format.model_validate_json(result.text)
                except ValidationError as exc:
                    logger.warning("Speaking structured output validation failed: %s", exc)

        return result


speaking_pipeline = SpeakingPipeline()
