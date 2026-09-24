from __future__ import annotations

import pytest

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Sprite, SpriteFrame
from simulator.entities.plate import plated_parts
from simulator.entities.sprite import SpriteDefinition, SpriteFramePart
from simulator.view import (
    badge_order,
    controller_for_agent,
    fit_to_cell,
    score_view,
    seat_on_cell,
    sprite_icon,
    timeline_view,
)
from tests.status_levels import LEVEL
from tests.stub_controller import StubController


def test_open_ended_runs_read_as_live_and_sit_at_the_end() -> None:
    environment = load(Configuration.from_dict({"layout": "| |"}))

    view = timeline_view(environment.copy_with(timestep=42), rate_label="1 step / key")

    assert view.total is None
    assert view.position_label == "Live"
    assert view.progress == 1.0


def test_replay_reports_a_real_position() -> None:
    environment = load(Configuration.from_dict({"layout": "| |"}))

    view = timeline_view(environment.copy_with(timestep=25), total=100)

    assert view.position_label == "25 / 100"
    assert view.progress == pytest.approx(0.25)


def test_progress_is_clamped_past_the_end() -> None:
    environment = load(Configuration.from_dict({"layout": "| |"}))

    view = timeline_view(environment.copy_with(timestep=180), total=100)

    assert view.progress == 1.0


def test_reports_score_and_deliveries() -> None:
    environment = load(Configuration.from_dict({"layout": "| |"}))

    score = score_view(environment)

    assert score.score == 0
    assert score.delivered == 0


def _sprite(*parts: SpriteFramePart) -> Sprite:
    return Sprite(loop_cycle_animation=[SpriteFrame(parts=list(parts))])


def _one_part_sprite(width: int, height: int) -> Sprite:
    return _sprite(SpriteFramePart(x=0, y=0, width=width, height=height))


def test_a_sprite_that_sits_in_its_cell_asks_for_no_margin() -> None:
    _, pad = fit_to_cell(_one_part_sprite(16, 16))

    assert pad == 0


def test_a_lifted_sprite_stays_lifted_and_the_margin_makes_room() -> None:
    # The point of the whole arrangement. A dish drawn four pixels up is drawn
    # four pixels up in a panel too, rather than being slid back to the middle
    # of a box cut to fit it.
    sprite = _sprite(SpriteFramePart(x=0, y=0, width=16, height=16, shift_y=-4))

    fitted, pad = fit_to_cell(sprite)

    assert pad == 4
    assert [part.shift_y for part in fitted.loop_cycle_animation[0].parts] == [-4]


def test_the_margin_covers_the_worst_side_and_is_the_same_all_round() -> None:
    # Padding one side alone would move the cell off the middle of the canvas,
    # and the slot centres the canvas, so the art would come back to centre by
    # the back door.
    sprite = _sprite(SpriteFramePart(x=0, y=0, width=32, height=16, shift_y=-3))

    _, pad = fit_to_cell(sprite)

    assert pad == 16


def test_an_empty_sprite_asks_for_nothing() -> None:
    fitted, pad = fit_to_cell(Sprite())

    assert pad == 0
    assert fitted == Sprite()


def test_an_icon_holds_a_cell_and_pads_it_by_the_overhang() -> None:
    sprite = _sprite(SpriteFramePart(x=0, y=0, width=16, height=16, shift_y=-4))

    transform = sprite_icon(sprite, scale=3)._props["transform"]

    assert (transform["grid_width"], transform["grid_height"]) == (1, 1)
    assert transform["unit"] == 16
    assert transform["pad"] == 4
    assert transform["scale"] == 3


def test_a_station_drawn_where_it_stands_is_moved_onto_its_cell() -> None:
    # An oven hangs most of its height above the cell it occupies, which is
    # about the counter under it. An icon has no counter.
    parts = seat_on_cell([SpriteFramePart(x=0, y=0, width=16, height=32, shift_y=-13)])

    assert [part.shift_y for part in parts] == [-8]


def test_seating_a_station_keeps_its_parts_where_they_were_put() -> None:
    # A stand mixer is a base and a head with a gap between them, and the gap is
    # the sprite. Only the pair as a whole moves.
    parts = seat_on_cell(
        [
            SpriteFramePart(x=0, y=0, width=16, height=16, shift_y=-16),
            SpriteFramePart(x=0, y=0, width=16, height=16, shift_y=-32),
        ]
    )

    assert [part.shift_y for part in parts] == [8, -8]


def test_a_ticket_stands_its_dish_on_the_plate_rather_than_over_it() -> None:
    # The gap is the whole of what reads as plated, and the kitchen and the
    # order tickets have to agree on it or a ticket shows a dish the player
    # never sees.
    food = SpriteDefinition(parts=[SpriteFramePart(x=0, y=0, width=16, height=16)])

    plate, dish = plated_parts(food)

    assert dish.shift_y == plate.shift_y - 3


def test_a_plate_with_nothing_on_it_is_still_a_plate() -> None:
    assert len(plated_parts()) == 1


def test_composite_resolves_each_agent_to_its_own_controller() -> None:
    from simulator.composite_controller import CompositeController

    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]
    first, second = StubController(busy=True), StubController()
    composite = CompositeController([(first, [order[0]]), (second, [order[1]])])

    assert controller_for_agent(composite, order[0]) is first
    assert controller_for_agent(composite, order[1]) is second


def test_a_lone_controller_owns_every_agent() -> None:
    environment = load(Configuration.from_dict(LEVEL))
    order = [agent.id for agent in badge_order(environment)]
    controller = StubController()

    for agent_id in order:
        assert controller_for_agent(controller, agent_id) is controller


def test_unowned_agents_resolve_to_nothing() -> None:
    controller = StubController()
    controller.set_controlled_agents(["someone-else"])

    assert controller_for_agent(controller, "agent-1") is None
