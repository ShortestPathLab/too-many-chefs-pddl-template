"""Test terminal status output and ``--quiet``."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from simulator import console


@pytest.fixture(autouse=True)
def _restore_quiet() -> Iterator[None]:
    """Restore the process-wide quiet setting after the test."""
    yield
    console.set_quiet(False)


def _spoken(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().out


def test_a_warning_reaches_a_terminal_nobody_has_quietened(
    capsys: pytest.CaptureFixture[str],
) -> None:
    console.warn("the pan is on fire")

    assert "the pan is on fire" in _spoken(capsys)


def test_quiet_stops_the_warning(capsys: pytest.CaptureFixture[str]) -> None:
    console.set_quiet()

    console.warn("the pan is on fire")

    assert _spoken(capsys) == ""


def test_quiet_stops_the_panel(capsys: pytest.CaptureFixture[str]) -> None:
    console.set_quiet()
    status = console.ViewerStatus(
        "http://127.0.0.1:8080/",
        8080,
        count_viewers=lambda: 0,
        windowed=False,
    )

    status.start()
    status.stop()

    assert _spoken(capsys) == ""


def test_the_panel_prints_the_link_when_nobody_has_quietened_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = console.ViewerStatus(
        "http://127.0.0.1:8080/",
        8080,
        count_viewers=lambda: 0,
        windowed=False,
    )

    status.start()
    status.stop()

    assert "http://127.0.0.1:8080/" in _spoken(capsys)


def test_quiet_is_a_switch_and_can_be_put_back() -> None:
    console.set_quiet()
    assert console.is_quiet()

    console.set_quiet(False)
    assert not console.is_quiet()
