"""Test per-agent and kitchen scores."""

from __future__ import annotations

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent, Food, Plate
from simulator.mutations import Cook, Deliver, TakeFromStorage
from simulator.run.result import build_simulation_result
from simulator.view import agents_view, badge_order, summary_view
from tests.scoring_states import SALAD, TOMATO, scoring_state
from tests.team_kitchens import (
    DELIVERY_KITCHEN,
    TWO_CHEF_KITCHEN,
    state_of,
    two_chefs,
)


def test_each_chef_is_paid_for_their_own_step() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN)

    retrieved = TakeFromStorage(agent_id=first.id).run(environment)
    chopped = Cook(agent_id=second.id).run(retrieved)
    state = state_of(chopped)

    assert state.score == 7
    assert state.score_by_agent == {first.id: 2, second.id: 5}


def test_the_kitchen_total_is_what_the_chefs_add_up_to() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN)

    retrieved = TakeFromStorage(agent_id=first.id).run(environment)
    chopped = Cook(agent_id=second.id).run(retrieved)
    scoring = state_of(chopped).scoring

    assert scoring.total_for([first.id, second.id]) == scoring.score
    assert scoring.total_for([second.id]) == 5


def test_a_chef_who_never_scored_is_worth_zero_rather_than_missing() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN)

    retrieved = TakeFromStorage(agent_id=first.id).run(environment)
    scoring = state_of(retrieved).scoring

    assert scoring.score_for(second.id) == 0
    assert scoring.total_for([second.id]) == 0


def test_a_payout_with_no_chef_behind_it_reaches_the_till_only() -> None:
    state = scoring_state()

    retrieved = state.notify_item_retrieved(TOMATO)

    assert retrieved.score == 2
    assert retrieved.score_by_agent == {}


def test_delivering_pays_the_chef_who_carried_the_plate() -> None:
    environment, first, second = two_chefs(DELIVERY_KITCHEN)
    food = Food(name=SALAD, x=None, y=None)
    plate = Plate(x=None, y=None, held_item_id=food.id)
    environment = (
        environment.with_entity(food)
        .with_entity(plate)
        .replace_entity(second.copy_with(held_item_id=plate.id))
    )

    delivered = Deliver(agent_id=second.id).run(environment)
    state = state_of(delivered)

    assert state.score == 50
    assert state.score_by_agent == {second.id: 50}
    assert state.score_for(first.id) == 0


def test_the_agent_panel_shows_a_chef_their_own_takings() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN)
    chopped = Cook(agent_id=second.id).run(
        TakeFromStorage(agent_id=first.id).run(environment)
    )

    view = agents_view(chopped, order=[first.id, second.id])

    assert [agent.score for agent in view.agents] == [2, 5]


def test_the_result_lists_every_chef_in_badge_order() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN)
    chopped = Cook(agent_id=second.id).run(environment)

    result = build_simulation_result(
        chopped,
        reason="completed",
        elapsed_seconds=1.0,
        agent_order=[agent.id for agent in badge_order(environment)],
    )

    assert list(result.score_by_agent) == [first.id, second.id]
    assert result.score_by_agent == {first.id: 0, second.id: 5}
    assert result.score == 5


def test_the_ending_card_numbers_the_chefs_the_way_the_badges_do() -> None:
    environment, first, second = two_chefs(TWO_CHEF_KITCHEN)
    chopped = Cook(agent_id=second.id).run(
        TakeFromStorage(agent_id=first.id).run(environment)
    )

    card = summary_view(
        build_simulation_result(
            chopped,
            reason="completed",
            elapsed_seconds=1.0,
            agent_order=[first.id, second.id],
        )
    )

    assert card.split_worth_showing
    assert [(agent.number, agent.agent_id, agent.score) for agent in card.agents] == [
        (1, first.id, 2),
        (2, second.id, 5),
    ]


def test_one_chef_earning_everything_needs_no_breakdown() -> None:
    environment = load(
        Configuration.from_dict(
            {"layout": "|1| |", "legend": {"agents": [{"symbol": "1"}]}}
        )
    )
    agent = environment.get_first_entity_of_type(Agent)
    assert agent is not None

    card = summary_view(
        build_simulation_result(environment, reason="stopped", elapsed_seconds=0.5)
    )

    assert [agent.agent_id for agent in card.agents] == [agent.id]
    assert not card.split_worth_showing
