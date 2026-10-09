from __future__ import annotations

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent, Equipment, Food, Plate, Sprite
from simulator.environment import Environment
from simulator.view import agents_view, badge_order
from tests.status_levels import KITCHEN, LEVEL, PAN, PATTY
from tests.stub_controller import StubController


def test_numbering_survives_agents_swapping_places() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]
    assert len(order) == 2

    # Move the second agent left of the first, so a live positional sort
    # would swap them.
    first, second = (
        environment.get_entity_as(order[0], Agent),
        environment.get_entity_as(order[1], Agent),
    )
    assert first is not None and second is not None
    moved = environment.with_entity(second.copy_with(x=-5))

    view = agents_view(moved, order=order)

    assert [agent.agent_id for agent in view.agents] == order
    assert [agent.number for agent in view.agents] == [1, 2]


def test_reports_selection_and_empty_hands() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]

    view = agents_view(environment, order=order, selected_agent_id=order[1])

    assert view.selected_index == 1
    assert view.agents[1].selected
    assert view.agents[0].held_label == "Empty"
    assert view.agents[0].held_sprite is None


def test_controller_is_absent_when_none_is_running() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]

    view = agents_view(environment, order=order)

    assert view.agents[0].controller is None


def test_controller_reports_label_and_plan_progress() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]
    controller = StubController(busy=True, progress=(3, 12))

    view = agents_view(environment, order=order, controller=controller)

    reported = view.agents[0].controller
    assert reported is not None
    assert reported.label == "Stub"
    assert reported.status_label == "Planning"
    assert (reported.progress or 0.0) == pytest.approx(0.25)


def test_a_controller_part_way_through_a_plan_reads_as_executing() -> None:
    # Not busy, because the solver has already returned. Not idle either.
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]
    controller = StubController(busy=False, progress=(4, 10))

    reported = (
        agents_view(environment, order=order, controller=controller)
        .agents[0]
        .controller
    )
    assert reported is not None
    assert reported.status_label == "Executing"
    assert reported.active


def test_a_finished_plan_is_not_executing() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]
    controller = StubController(busy=False, progress=(10, 10))

    reported = (
        agents_view(environment, order=order, controller=controller)
        .agents[0]
        .controller
    )
    assert reported is not None
    assert not reported.executing


def test_controller_without_a_plan_reports_no_progress() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]

    view = agents_view(environment, order=order, controller=StubController())

    reported = view.agents[0].controller
    assert reported is not None
    assert reported.progress is None
    assert reported.status_label == "Idle"


def test_a_controller_that_says_it_is_done_reads_as_finished() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]
    controller = StubController(finished=True, progress=(10, 10))

    reported = (
        agents_view(environment, order=order, controller=controller)
        .agents[0]
        .controller
    )
    assert reported is not None
    assert reported.status_label == "Finished"


# Panel data for a composite held item.
def _holding(*entities) -> tuple[Environment, list[str]]:
    """Return a kitchen with the chef holding the first entity."""
    environment = load(Configuration.from_dict(KITCHEN))
    order = [agent.id for agent in badge_order(environment)]
    agent = environment.get_entity_as(order[0], Agent)
    assert agent is not None

    for entity in entities:
        environment = environment.with_entity(entity)
    return (
        environment.with_entity(agent.copy_with(held_item_id=entities[0].id)),
        order,
    )


def _held(environment: Environment, order: list[str]):
    return agents_view(environment, order=order).agents[0]


def _sheets(sprite: Sprite | None) -> set[str]:
    assert sprite is not None
    return {part.sheet for frame in sprite.loop_cycle_animation for part in frame.parts}


def test_a_loose_ingredient_shows_its_own_sprite() -> None:
    environment, order = _holding(Food(id="patty", name=PATTY))

    held = _held(environment, order)

    assert held.held_label == "Patty"
    assert _sheets(held.held_sprite) == {"food.png"}


def test_a_plated_dish_shows_the_plate_and_the_dish() -> None:
    environment, order = _holding(
        Plate(id="plate", held_item_id="patty"),
        Food(id="patty", name=PATTY),
    )

    held = _held(environment, order)

    assert held.held_label == "Plate / Patty"
    # The plate comes off the interiors sheet, the patty off the food one.
    assert _sheets(held.held_sprite) == {"interiors.png", "food.png"}


def test_an_empty_plate_is_still_a_plate() -> None:
    environment, order = _holding(Plate(id="plate"))

    held = _held(environment, order)

    assert held.held_label == "Plate"
    assert _sheets(held.held_sprite) == {"interiors.png"}


def test_a_pan_shows_what_is_cooking_in_it() -> None:
    environment, order = _holding(
        Equipment(id="pan", name=PAN, can_pick_up=True, held_item_id="patty"),
        Food(id="patty", name=PATTY),
    )

    held = _held(environment, order)

    assert held.held_label == "Pan / Patty"
    assert _sheets(held.held_sprite) == {"custom.png", "food.png"}


def test_an_empty_pan_still_shows_the_pan() -> None:
    environment, order = _holding(Equipment(id="pan", name=PAN, can_pick_up=True))

    held = _held(environment, order)

    assert held.held_label == "Pan"
    assert _sheets(held.held_sprite) == {"custom.png"}


def test_equipment_the_level_never_drew_leaves_the_slot_empty() -> None:
    environment, order = _holding(
        Equipment(id="gadget", name="catalog/equipment/gadget", can_pick_up=True)
    )

    held = _held(environment, order)

    assert held.held_label == "Gadget"
    assert held.held_sprite is None
