"""Test level loading and draw order."""

from __future__ import annotations

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import load, load_configuration
from simulator.entities import Bounds, Counter, Equipment, Shadows
from simulator.view import OVERLAY_SUFFIX, ordered_game_objects, scene_layers


def test_load_adds_one_separate_shadows_entity() -> None:
    configuration = Configuration.from_dict({"layout": "| |"})

    environment = load(configuration)
    environment = load(configuration, environment)
    environment = environment.with_entity(Equipment(x=0, y=0))

    shadows = environment.get_entities_of_type(Shadows)
    assert len(shadows) == 1
    assert shadows[0].id == "shadows"

    bounds = environment.get_first_entity_of_type(Bounds)
    assert bounds is not None
    assert bounds is not None
    bounds_parts = bounds.sprite(environment, []).loop_cycle_animation[0].parts
    shadow_parts = shadows[0].sprite(environment, []).loop_cycle_animation[0].parts
    # The first part is the full-sized backdrop, then one base tile per cell,
    # then the floor tiles laid over them.
    cells = 1
    assert bounds_parts[0].sheet.startswith("backgrounds/background_")
    assert all(part.sheet == "custom.png" for part in bounds_parts[1 : 1 + cells])
    assert all(part.sheet == "room_builder.png" for part in bounds_parts[1 + cells :])
    assert len(shadow_parts) == 1
    assert all(part.sheet == "shadows.png" for part in shadow_parts)


def test_ordered_game_objects_preserves_stacked_equipment_order() -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "|SP|",
            "legend": {
                "equipment": [
                    {
                        "kind": "equipment",
                        "symbol": "S",
                        "name": "catalog/equipment/stove",
                    },
                    {
                        "kind": "equipment",
                        "symbol": "P",
                        "name": "catalog/equipment/pan",
                        "can_pick_up": True,
                    },
                ],
                "foods": [{"kind": "food", "name": "catalog/food/tomato"}],
            },
        }
    )

    environment = load(configuration)

    names = [
        entity.name
        for entity in ordered_game_objects(environment)
        if isinstance(entity, Equipment)
    ]
    assert names == ["catalog/equipment/stove", "catalog/equipment/pan"]


def test_ordered_game_objects_prioritises_draw_layer_over_y() -> None:
    configuration = Configuration.from_dict(
        {
            "layout": "|E|\n|C|",
            "legend": {
                "equipment": [
                    {
                        "kind": "equipment",
                        "symbol": "E",
                        "name": "catalog/equipment/pan",
                        "can_pick_up": True,
                    }
                ],
                "counters": [{"kind": "counter", "symbol": "C"}],
                "foods": [{"kind": "food", "name": "catalog/food/tomato"}],
            },
        }
    )

    environment = load(configuration)
    ordered = ordered_game_objects(environment)

    counter_index = next(
        index for index, entity in enumerate(ordered) if isinstance(entity, Counter)
    )
    equipment_index = next(
        index for index, entity in enumerate(ordered) if isinstance(entity, Equipment)
    )
    assert counter_index < equipment_index


def _stacked_mixer() -> Configuration:
    return Configuration.from_dict(
        {
            "layout": "|MB|",
            "legend": {
                "equipment": [
                    {
                        "kind": "equipment",
                        "symbol": "M",
                        "name": "catalog/equipment/mixer",
                        "sprite": [{"x": 48, "y": 154, "width": 20, "height": 8}],
                        "overlay": [{"x": 48, "y": 138, "width": 20, "height": 16}],
                    },
                    {
                        "kind": "equipment",
                        "symbol": "B",
                        "name": "catalog/equipment/mixing_bowl",
                        "can_pick_up": True,
                        "sprite": [{"x": 16, "y": 112}],
                    },
                ],
                "foods": [{"kind": "food", "name": "catalog/food/tomato"}],
            },
        }
    )


def _equipment_named(environment, name: str) -> Equipment:
    return next(
        entity
        for entity in environment.get_entities_of_type(Equipment)
        if entity.name == name
    )


def test_an_overlay_brackets_whatever_is_stacked_on_its_station() -> None:
    # The whole point of the second renderable: a bowl set down on a stand mixer
    # has to pass in front of the base and behind the head. One renderable draws
    # its parts in a single run, so nothing can sit between them.
    environment = load(_stacked_mixer())
    mixer = _equipment_named(environment, "catalog/equipment/mixer")
    bowl = _equipment_named(environment, "catalog/equipment/mixing_bowl")

    objects = {
        renderable.id: renderable for renderable in scene_layers(environment).objects
    }
    overlay = objects[f"{mixer.id}{OVERLAY_SUFFIX}"]

    assert objects[mixer.id].z < objects[bowl.id].z < overlay.z
    assert (overlay.x, overlay.y) == (objects[mixer.id].x, objects[mixer.id].y)
    assert [part.y for part in overlay.sprite.loop_cycle_animation[0].parts] == [138]


def test_a_station_without_an_overlay_draws_one_renderable() -> None:
    environment = load(
        Configuration.from_dict(
            {
                "layout": "|S|",
                "legend": {
                    "equipment": [
                        {
                            "kind": "equipment",
                            "symbol": "S",
                            "name": "catalog/equipment/stove",
                            "sprite": [{"x": 128, "y": 4288}],
                        }
                    ],
                    "foods": [{"kind": "food", "name": "catalog/food/tomato"}],
                },
            }
        )
    )

    ids = [renderable.id for renderable in scene_layers(environment).objects]
    assert [id for id in ids if id.endswith(OVERLAY_SUFFIX)] == []


def test_the_catalog_carries_overlay_parts_through_the_merge() -> None:
    # The catalog reaches a level by round-tripping through the configuration's
    # aliases, so a field that serialises under the wrong name reads as a
    # station with no overlay rather than as an error.
    configuration = load_configuration("levels/demos/black_forest_cake.yaml")

    mixer = next(
        entry
        for entry in configuration.legend.equipment
        if entry.name == "catalog/equipment/mixer"
    )
    assert mixer.overlay_parts != []
