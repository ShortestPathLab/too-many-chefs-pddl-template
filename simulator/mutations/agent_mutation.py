from __future__ import annotations

from typing import Any

from simulator.mutations.mutation import Mutation


class AgentMutation(Mutation):
    agent_id: str
    expected_held_food: str | None = None
    expected_input_name: str | None = None
    expected_output_name: str | None = None
    expected_held_equipment_name: str | None = None
    expected_held_equipment_contents_name: str | None = None
    expected_target_food_name: str | None = None
    expected_target_equipment_name: str | None = None
    expected_target_equipment_contents_name: str | None = None

    @property
    def agent_mutation_args(self) -> dict[str, Any]:
        a = self.to_dict()
        a.pop("kind")
        return a
