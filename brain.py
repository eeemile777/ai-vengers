# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "datapizza-ai",
#     "datapizza-ai-clients-openai-like",
#     "python-dotenv"
# ]
# ///

import json
import os
from typing import Any

from dotenv import load_dotenv

# CRITICAL: Set tracing BEFORE importing datapizza.clients
os.environ["DATAPIZZA_TRACE_CLIENT_IO"] = "TRUE"

# Load environment variables
load_dotenv()

# Initialize the Regolo.ai LLM
from datapizza.clients.openai_like import OpenAILikeClient

llm_client = OpenAILikeClient(
    api_key=os.getenv("REGOLO_API_KEY"),
    model="gpt-oss-120b",
    base_url="https://api.regolo.ai/v1",
)


##########################################################################################
#                         AI DECISION-MAKING ENGINE                                      #
##########################################################################################


async def make_order_decision(order_context: dict[str, Any]) -> dict[str, Any]:
    """
    Use LLM to intelligently parse a client's order.
    Match order text to menu, verify intolerances, determine if we can serve.
    DO NOT use naive string replace - let the LLM understand complex orders.
    """
    from main import log
    
    prompt = f"""
You are parsing a client's order at a galactic restaurant.

CLIENT REQUEST:
- Name: {order_context.get('client_name', 'Unknown')}
- Order Text: {order_context.get('order_text', '')}
- Intolerances: {json.dumps(order_context.get('intolerances', []))}

OUR MENU:
{json.dumps(order_context.get('menu_items', []), indent=2)}

Your task:
1. Parse the order text and identify which dish the client is requesting
2. Check if the dish exists in our menu
3. Verify the dish does NOT contain any ingredients the client is intolerant to
4. Respond with ONLY valid JSON:
{{
  "dish_name": "exact menu dish name or null if cannot determine",
  "can_serve": true/false,
  "intolerance_safe": true/false,
  "reason": "brief explanation if cannot serve"
}}
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        
        # Use official datapizza-ai async method
        response = await llm_client.a_invoke({"messages": messages})
        
        # Strip markdown backticks that LLM might wrap around JSON
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]  # Remove ```json prefix
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]  # Remove ``` prefix
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]  # Remove ``` suffix
        raw_text = raw_text.strip()
        
        decision = json.loads(raw_text)
        log("LLM_ORDER", f"Order parsed: {decision.get('dish_name')}")
        return decision
    except json.JSONDecodeError as exc:
        log("LLM_ERROR", f"Failed to parse order decision JSON: {exc}")
        return {"error": "Invalid JSON", "can_serve": False, "dish_name": None}
    except Exception as exc:
        log("LLM_ERROR", f"Order parsing failed: {exc}")
        return {"error": str(exc), "can_serve": False, "dish_name": None}


async def make_llm_decision(phase: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Use the LLM to make autonomous decisions based on current phase and context.
    Returns a structured decision with recommended actions.
    Uses official datapizza-ai async execution method.
    """
    from main import log
    
    system_prompt = f"""
You are the autonomous AI Chef and General Manager of a galactic restaurant in Cosmic Cycle 790.

CURRENT PHASE: {phase}
YOUR MISSION: Maximize the restaurant's balance (saldo).

THE 5 GOLDEN RULES:
1. Ingredients expire every turn - NEVER hoard, only buy what you'll cook NOW
2. Check client intolerances strictly - serving wrong dishes causes diplomatic incidents
3. Master the market - snipe cheap ingredients, dump excess inventory
4. Use the panic button - close restaurant if overwhelmed (better than bad service)
5. Execute phase-by-phase - only perform actions allowed in current phase

CONTEXT:
{json.dumps(context, indent=2)}

Based on the current phase and context, decide what actions to take.

OUTPUT FORMAT: You MUST return a JSON object with EXACTLY these keys (leave lists empty if no action is needed):
{{
  "reasoning": "string explaining your decision",
  "menu": [{{"name": "string", "price": 0}}],
  "bid_ingredients": [{{"ingredient": "string", "bid": 0, "quantity": 0}}],
  "market_buys": [{{"ingredient": "string", "quantity": 0, "price": 0}}],
  "market_sells": [{{"ingredient": "string", "quantity": 0, "price": 0}}],
  "messages": [{{"recipient": 0, "content": "string"}}]
}}

RESPOND ONLY WITH VALID JSON. No markdown. No extra text.
"""

    user_prompt = f"What actions should I take in the {phase} phase? Provide specific tool calls with exact arguments. Return ONLY valid JSON."

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Use official datapizza-ai async method a_invoke (not chat_completion)
        response = await llm_client.a_invoke({"messages": messages})
        
        # Strip markdown backticks that LLM might wrap around JSON
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]  # Remove ```json prefix
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]  # Remove ``` prefix
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]  # Remove ``` suffix
        raw_text = raw_text.strip()
        
        decision = json.loads(raw_text)
        log("LLM", f"Decision made for {phase} phase")
        return decision
    except json.JSONDecodeError as exc:
        log("LLM_ERROR", f"Failed to parse LLM response as JSON: {exc}")
        return {"error": "Invalid JSON response", "actions": []}
    except Exception as exc:
        log("LLM_ERROR", f"Decision making failed: {exc}")
        return {"error": str(exc), "actions": []}
