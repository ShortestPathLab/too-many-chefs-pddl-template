"""Kitchens for agent traffic tests."""

from __future__ import annotations

from simulator.entities import Agent, Bounds
from simulator.environment import Environment
from simulator.mutations import Mutation, MutationWithLocation
from simulator.types import Location


def chef(
    chef_id: str,
    x: int,
    y: int,
    *,
    orientation: str = "n",
    costume: str = "blue",
) -> Agent:
    return Agent(id=chef_id, x=x, y=y, orientation=orientation, costume=costume)


def kitchen(width: int, height: int, *chefs: Agent) -> Environment:
    """Return an empty floor with agents at the given positions."""
    environment = Environment().with_entity(
        Bounds(id="bounds", x=0, y=0, width=width, height=height)
    )
    for standing in chefs:
        environment = environment.with_entity(standing)
    return environment


def planned(
    index: int,
    mutation: Mutation,
    *,
    at: Location | None = None,
) -> tuple[int, MutationWithLocation]:
    """Return one planned step at its original position."""
    return (index, MutationWithLocation(mutation=mutation, location=at))


def chef_location(environment: Environment, chef_id: str) -> Location:
    agent = environment.get_entity_as(chef_id, Agent)
    assert agent is not None
    assert agent.x is not None
    assert agent.y is not None
    return (agent.x, agent.y)
