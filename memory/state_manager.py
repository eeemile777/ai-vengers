from dataclasses import dataclass, field
from typing import Any


@dataclass
class StateManager:
    turn_id: int = 0
    phase: str = "unknown"
    recipes: list[dict[str, Any]] = field(default_factory=list)
    prepared_dishes: list[str] = field(default_factory=list)
    active_clients: dict[str, dict[str, Any]] = field(default_factory=dict)

    def reset_turn_state(self) -> None:
        self.prepared_dishes.clear()
        self.active_clients.clear()

    def on_game_reset(self) -> None:
        self.turn_id = 0
        self.phase = "unknown"
        self.reset_turn_state()


state_manager = StateManager()