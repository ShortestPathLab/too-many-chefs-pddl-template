from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load
from simulator.entities import Agent, Bounds, Counter, Equipment, Food, Plate, Walls


def test_level_appearance_configures_base_tiles() -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "| - |",
            "appearance": {
                "floor_type": 3,
                "wall_type": 4,
                "counter_wood_variant": 5,
            },
            "legend": {
                "counters": [{"kind": "counter", "symbol": "-"}],
            },
        }
    )
    environment = load(configuration)

    bounds = environment.get_first_entity_of_type(Bounds)
    walls = environment.get_first_entity_of_type(Walls)
    counter = environment.get_first_entity_of_type(Counter)

    assert bounds is not None
    assert walls is not None
    assert counter is not None
    assert bounds is not None
    assert walls is not None
    assert counter is not None
    assert bounds.floor_type == 3
    assert walls.wall_type == 4
    assert counter.wood_variant == 5


def test_every_order_has_a_plate() -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "| p | p |",
            "state": {
                "orders": [
                    "catalog/food/tomato",
                    "catalog/food/onion",
                ]
            },
            "legend": {
                "plates": [{"kind": "plate", "symbol": "p"}],
                "foods": [
                    {
                        "kind": "food",
                        "name": "catalog/food/tomato",
                    },
                    {
                        "kind": "food",
                        "name": "catalog/food/onion",
                    },
                ],
            },
        }
    )
    environment = load(configuration)

    plate_count = len(environment.get_entities_of_type(Plate))
    assert plate_count >= len(configuration.state.orders)


def test_food_a_level_puts_in_a_pan_on_a_stove_belongs_to_the_pan() -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "| VP |",
            "legend": {
                "equipment": [
                    {"symbol": "V", "name": "catalog/equipment/stove"},
                    {
                        "symbol": "P",
                        "name": "catalog/equipment/pan",
                        "requires": "catalog/equipment/stove",
                        "held_item": {"name": "catalog/food/meat"},
                    },
                ],
                "foods": [{"name": "catalog/food/meat"}],
            },
        }
    )

    environment = load(configuration)
    holders = {
        equipment.name: equipment.held_item_id
        for equipment in environment.get_entities_of_type(Equipment)
    }
    [food] = environment.get_entities_of_type(Food)

    assert holders == {
        "catalog/equipment/stove": None,
        "catalog/equipment/pan": food.id,
    }


def test_a_chef_without_a_name_gets_the_same_id_every_load() -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "| 1 |   | 2 |",
            "legend": {
                "agents": [
                    {"kind": "agent", "symbol": "1"},
                    {"kind": "agent", "symbol": "2", "name": "bob"},
                ],
            },
        }
    )

    first = {agent.id for agent in load(configuration).get_entities_of_type(Agent)}
    second = {agent.id for agent in load(configuration).get_entities_of_type(Agent)}

    assert first == second == {"chef_0_0", "bob"}


def test_entities_whose_random_ids_start_alike_stay_apart() -> None:
    from unittest.mock import patch
    from uuid import UUID

    from simulator.entities import Entity

    alike = [
        UUID("abcd1111-0000-4000-8000-000000000000"),
        UUID("abcd2222-0000-4000-8000-000000000000"),
    ]
    with patch("simulator.entities.entity.uuid4", side_effect=alike):
        first, second = Entity(), Entity()

    assert first.id != second.id
