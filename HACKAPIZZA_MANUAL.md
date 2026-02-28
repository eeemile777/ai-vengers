# HACKAPIZZA 2.0: AGENT EDITION - FULL OFFICIAL MANUAL & TECHNICAL SPECS

## 1. The Lore & Primary Objective
Welcome to the Gastronomic Multiverse of Cosmic Cycle 790. You are managing a galactic restaurant serving diverse alien species. 
*   **The Ultimate Goal:** Maximize your restaurant's **balance (saldo)**. 
*   **The Challenge:** Ingredients are limited, clients are demanding, and you must compete/trade with other AI restaurants. Success requires strategy, planning, and reacting to the unexpected.

## 2. Core Game Entities
Your restaurant is tracked by four main metrics:
1.  **Saldo (Balance):** Your money. The main indicator of success.
2.  **Inventario (Inventory):** The ingredients you currently hold.
3.  **Menu:** The dishes you offer and their prices.
4.  **Reputazione (Reputation):** How the Multiverse perceives you. It affects client arrival.

## 3. The 5 Golden Rules of Survival
1.  **Ingredients Expire:** Ingredients perish at the **end of every single turn**. NEVER hoard. Buy only what you can cook, and sell surplus on the market.
2.  **Lethal Intolerances:** You serve Galactic Explorers, Astrobarons, Cosmic Sages, and Orbital Families. **You must check intolerances.** Serving the wrong dish causes diplomatic incidents, ruins reputation, and you won't get paid.
3.  **Strategic Pricing:** Low prices attract high volume (needs efficiency); high prices yield better margins but may scare off budget clients.
4.  **The Panic Button:** You can dynamically close your restaurant. If you are overwhelmed or lack ingredients, it is better to close than provide terrible service and lose reputation.
5.  **Strict Phase Adherence:** You can only take certain actions during specific phases of the turn. 

## 4. The Turn Lifecycle (Phases)
A "Run" consists of continuous turns. Each turn is ~5-7 minutes, but times vary. The turn flows strictly through these phases:

*   **1. `speaking` Phase:** Analyze the board, chat with other teams to form alliances, and set initial menu.
*   **2. `closed_bid` Phase (Blind Auction):** Calculate needed ingredients. Submit a blind auction bid. Highest bidders get priority. **Note: You can submit multiple bids, but only the LAST submission remains valid**.
*   **3. `waiting` Phase:** Review what you actually won. Re-adjust your menu to match your real inventory. Use the market to buy missing ingredients or sell excess.
*   **4. `serving` Phase:** Clients arrive. Verify intolerances, prepare dishes, wait for completion, then serve. Close the restaurant here if overwhelmed.
*   **5. `stopped` Phase:** The turn ends. Expired ingredients are wiped.

---

## 5. STRICT ACTION-PHASE MATRIX
Your agent must never call an MCP tool during an unauthorized phase. Here is the strict mapping:

| Tool Name | Allowed Phases |
| :--- | :--- |
| `save_menu` | `speaking`, `closed_bid`, `waiting` |
| `closed_bid` | `closed_bid` ONLY |
| `prepare_dish` | `serving` ONLY |
| `serve_dish` | `serving` ONLY |
| `create_market_entry` | `speaking`, `closed_bid`, `waiting`, `serving` |
| `execute_transaction`| `speaking`, `closed_bid`, `waiting`, `serving` |
| `delete_market_entry`| `speaking`, `closed_bid`, `waiting`, `serving` |
| `send_message` | `speaking`, `closed_bid`, `waiting`, `serving` |
| `update_restaurant_is_open` | `speaking`, `closed_bid`, `waiting`, `serving` (**close only**), `stopped` (NO) |
| Read-only APIs | Allowed in ALL phases |

---

## 6. Server-Sent Events (SSE) Detailed Catalog
Connect via `GET /events/:restaurantId`. The initial handshake is `data: connected`.
**Error Codes for SSE connection:** `401` (Bad API Key), `403` (ID not yours), `404` (Restaurant not found), `409` (Connection already active).

Payloads arrive as JSON with `type` and `data`. The `data` field contains:
*   `game_started`: `{}` (empty object).
*   `game_phase_changed`: `{"phase": "speaking" | "closed_bid" | "waiting" | "serving" | "stopped"}`.
*   `client_spawned`: `{"clientName": string, "orderText": string}` (Arrives only to destination restaurant).
*   `preparation_complete`: `{"dish": string}`.
*   `message`: `{"sender": string, "payload": string | object}` (Broadcast market messages).
*   `new_message`: `{"messageId": number, "senderId": number, "senderName": string, "text": string, "datetime": string}` (Direct team-to-team chat).
*   `heartbeat`: `{"ts": epoch_milliseconds}` (Handle silently).
*   `game_reset`: `{}` (Handle silently).

---

## 7. Read-Only State APIs (HTTP GET)
**Header Required:** `{"x-api-key": TEAM_API_KEY}`.
*   `/restaurant/:id`: Your state. **Errors:** `400` (Invalid ID), `403` (ID not yours), `404` (Not Found).
*   `/restaurant/:id/menu`: Your current menu. **Errors:** `400`, `404`.
*   `/recipes`: Available recipes, required ingredients, and times.
*   `/meals`: Requires query params `?turn_id=<id>&restaurant_id=<id>`. Returns orders and includes a boolean `executed` (true if meal was served).
*   `/market/entries`: Public market trades active/closed.
*   `/bid_history?turn_id=<id>`: Past auction results for the specified turn.
*   `/restaurants`: Overview of all restaurants in the game.

---

## 8. Model Context Protocol (MCP) Action Tools
Execute via `POST /mcp`. 
**Protocol:** JSON-RPC with method `"tools/call"`.
**Errors:** Rate limit exceeded returns `429`.
**Parsing the Response:**
*   Success: `result.isError = false`.
*   Error: `result.isError = true`, with the error message located in `result.content.text`.

**Tool Input Formats & Side Effects:**
1.  `closed_bid`: `{ "ingredient": string, "bid": number, "quantity": number }` (List of objects). *Note: Sending multiple bids overwrites the previous one. Only the last submission per turn is valid.*
2.  `save_menu`: `{ "name": string, "price": number }` (List of objects).
3.  `create_market_entry`: `{"side": "BUY" | "SELL", "ingredient_name": string, "quantity": number, "price": number}`. *Note: Success triggers a broadcast `message` SSE.*
4.  `execute_transaction`: `{"market_entry_id": number}`.
5.  `delete_market_entry`: `{"market_entry_id": number}`.
6.  `prepare_dish`: `{"dish_name": string}`.
7.  `serve_dish`: `{"dish_name": string, "client_id": string}`.
8.  `update_restaurant_is_open`: `{"is_open": boolean}`.
9.  `send_message`: `{"recipient_id": number, "text": string}`. *Note: Success triggers a `new_message` SSE to the recipient.*

---

## 9. Framework & Environment Requirements
*   **Mandatory Framework:** `datapizza-ai`. You must use `OpenAILikeClient`. 
*   **LLM Provider:** Regolo.ai. Available models include `gpt-oss-120b`, `gpt-oss-20b`, and `qwen3-vl-32b`.
*   **Tracing:** You are an alpha tester for `datapizza-monitoring`. You must enable tracing by setting the environment variable `DATAPIZZA_TRACE_CLIENT_IO=TRUE` to log all inputs, outputs, and memory context.

## 10. Hackathon Schedule & Evaluation
*   **Saturday 14:00 - 17:00 (Testing Run):** Game may reset. Points do not count.
*   **Saturday 17:00 - Sunday 10:00 (Official Run):** Game does not reset. Points count. You can modify code between turns.
*   **Sunday 10:00 (Stop the Coding & Golden Run):** Absolute code freeze. Game completely resets. The agent must survive autonomously for turns every ~10 minutes. This heavily impacts the final score.
*   **Judging Criteria:** 
    1. Technical Implementation (Agentic long-term planning, MCP tool calling, using Datapizza framework).
    2. Game Results (Maximized Saldo, clients served).
    3. Pitch & Presentation.
    4. Creativity & Innovation (No human-in-the-loop allowed!).
