from __future__ import annotations

from pathlib import Path

from simulator.configuration.configuration import Configuration
from simulator.configuration.load import (
    configuration_from_dict,
    load,
    load_configuration,
)
from simulator.configuration.load.catalog import load_equipment_catalog
from simulator.run.common import VISUAL_STEP_INTERVAL_MS
from simulator.view import (
    CUES,
    EQUIPMENT_CUE_PREFIX,
    EQUIPMENT_DEFAULT_CUE,
    cue_gains,
    cue_jitters,
    cue_repeats,
    cue_spreads,
    cue_urls,
    equipment_cues,
    missing_clips,
)
from tests.audio_kitchens import CUTBOARD_CUE, kitchen, with_cutboard_sound


def _audio_package_code() -> str:
    """Return audio module names with comments and strings removed."""
    import io
    import tokenize

    from simulator.view import audio

    directory = Path(audio.__file__).parent
    tokens = [
        token
        for path in sorted(directory.glob("*.py"))
        for token in tokenize.generate_tokens(
            io.StringIO(path.read_text(encoding="utf-8")).readline
        )
    ]
    return "\n".join(
        token.string
        for token in tokens
        if token.type not in (tokenize.COMMENT, tokenize.STRING)
    )


def test_every_cue_points_at_files_that_exist() -> None:
    assert missing_clips() == []


def test_cue_urls_are_served_from_the_audio_folder() -> None:
    for name, urls in cue_urls().items():
        assert urls, f"{name} has no clips"
        for url in urls:
            assert url.startswith("/assets/audio/"), f"{name} -> {url}"


def test_no_cue_is_loud_enough_to_clip_against_the_others() -> None:
    # Several cues can land on one step, and they are summed.
    assert sum(cue_gains().values()) <= len(CUES)
    for name, gain in cue_gains().items():
        assert 0 < gain <= 1, f"{name} -> {gain}"


def test_the_footstep_is_quieter_than_anything_it_repeats_under() -> None:
    gains = cue_gains()
    assert gains["move"] < gains["deliver"]
    assert gains["turn"] < gains["move"]


def test_the_footstep_is_thrown_wider_than_anything_else() -> None:
    # It is the only cue worth more than one sample, so it is the only one
    # with copies that need pulling apart.
    spreads = cue_spreads()
    others = [spread for name, spread in spreads.items() if name != "move"]

    assert spreads["move"] > max(others)


def test_no_cue_is_still_arriving_when_the_next_step_lands() -> None:
    # A copy that turns up after the step it belongs to has been replaced
    # reads as a mistimed sound rather than as a second chef.
    for name, spread in cue_spreads().items():
        assert 0 <= spread <= VISUAL_STEP_INTERVAL_MS / 1000, f"{name} -> {spread}"


def test_a_stride_is_heard_as_two_footfalls() -> None:
    # The chef crosses a tile on a six frame gait, so one sample under it
    # would be heard as a limp.
    assert cue_repeats()["move"] == 2


def test_nothing_but_the_footstep_is_worth_more_than_one_sample() -> None:
    for name, repeats in cue_repeats().items():
        assert repeats == (2 if name == "move" else 1), name


def test_the_audio_library_names_no_particular_equipment() -> None:
    # A new station should need nothing but a catalog entry. If a station
    # name turns up in the renderer's code, someone has taught it to care
    # about a fixed list again. Comments and docstrings are exempt: they can
    # name an oven as an example without hardcoding one.
    for station in ("cutboard", "oven", "deep_fryer", "mixer", "stove", "catalog/"):
        assert station not in _audio_package_code(), (
            f"the simulator/view/audio package has {station} written into it"
        )


def test_the_static_table_carries_no_equipment_cues() -> None:
    for cue in CUES:
        assert not cue.name.startswith(EQUIPMENT_CUE_PREFIX), cue.name
    assert equipment_cues(None) == ()


def test_a_station_brings_its_clips_with_the_level() -> None:
    environment = kitchen()

    urls = cue_urls(environment)

    assert urls[CUTBOARD_CUE] == [
        "/assets/audio/chop.ogg",
        "/assets/audio/knifeSlice.ogg",
    ]


def test_a_station_that_sets_no_numbers_inherits_them() -> None:
    environment = kitchen()
    gains, jitters = cue_gains(environment), cue_jitters(environment)

    assert gains[CUTBOARD_CUE] == gains[EQUIPMENT_DEFAULT_CUE]
    assert jitters[CUTBOARD_CUE] == jitters[EQUIPMENT_DEFAULT_CUE]


def test_a_station_can_set_its_own_level_and_spread() -> None:
    level = with_cutboard_sound({"clips": ["chop.ogg"], "gain": 0.9, "jitter": 0.2})
    environment = load(Configuration.from_dict(level))

    assert cue_gains(environment)[CUTBOARD_CUE] == 0.9
    assert cue_jitters(environment)[CUTBOARD_CUE] == 0.2


def test_one_filename_is_shorthand_for_a_list_of_one() -> None:
    environment = load(Configuration.from_dict(with_cutboard_sound("chop.ogg")))

    assert cue_urls(environment)[CUTBOARD_CUE] == ["/assets/audio/chop.ogg"]


def test_a_station_with_no_sound_contributes_no_cue() -> None:
    environment = load(Configuration.from_dict(with_cutboard_sound(None)))

    assert CUTBOARD_CUE not in cue_urls(environment)


def test_every_clip_the_shipped_catalog_names_exists() -> None:
    configuration = load_configuration(
        "levels/1_we_can_cook/2_chicken_and_chips_four_divided_4p.yaml"
    )
    environment = load(configuration)

    assert missing_clips(environment) == []
    assert CUTBOARD_CUE in cue_urls(environment)


def test_a_level_can_override_what_the_catalog_says() -> None:
    catalog = load_equipment_catalog(Path("catalog/equipment.yaml"))
    level = with_cutboard_sound("bookOpen.ogg")

    configuration = configuration_from_dict(level, equipment_catalog=catalog)
    environment = load(configuration)

    assert cue_urls(environment)[CUTBOARD_CUE] == ["/assets/audio/bookOpen.ogg"]
