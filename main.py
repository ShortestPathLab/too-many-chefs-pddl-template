from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from cli import (
    build_agent_controller,
    build_end_conditions,
    controller_assignments,
    controller_listing,
    describe_run,
    import_controllers,
    parse_controller_options,
    resolve_recording_output,
    resolve_run_outputs,
    teams_help,
    with_controller_options,
    with_teams,
)
from controllers import controller_plugins, default_controller_name
from simulator import console
from simulator.configuration import load, load_configuration
from simulator.context import Context
from simulator.match import (
    GAMES,
    MAX_TIMESTEPS,
    TICK_SECONDS,
    MatchSetupError,
    teams_of,
)
from simulator.recording import create_recording_sink, load_recording
from simulator.run import (
    RUN_ERRORS,
    ControllerAssignment,
    Episode,
    ErrorStage,
    RunError,
    RunSetup,
    SimulationResult,
    run_agent_mode,
)

app = typer.Typer(
    no_args_is_help=True,
    help="Too Many Chefs! The Open Kitchen Challenge",
)

WindowOption = Annotated[
    bool,
    typer.Option(
        "--window/--no-window",
        help=(
            "Open the kitchen in its own window. --no-window prints a URL to"
            " open in a browser instead."
        ),
    ),
]

# The heading over a failed run's traceback, by when the error came.
ERROR_TITLES: dict[ErrorStage, str] = {
    "import": "THE CONTROLLER'S CODE WOULD NOT IMPORT",
    "build": "THE CONTROLLER RAISED WHILE IT WAS BUILT",
    "run": "THE RUN ENDED WITH AN ERROR",
}

QuietOption = Annotated[
    bool,
    typer.Option(
        "--quiet",
        "-q",
        help=("Print nothing to the terminal other than the result JSON."),
    ),
]


@app.command()
def play(
    level: Annotated[
        Path,
        typer.Option(
            ...,
            prompt="Level to load, e.g. levels/demos/burger.yaml",
            exists=True,
            dir_okay=False,
            help="Path to a level YAML file, e.g. levels/demos/burger.yaml.",
        ),
    ],
    record: Annotated[
        bool,
        typer.Option(help="Enable recording to a YAML file."),
    ] = False,
    recording_out_file: Annotated[
        Path | None,
        typer.Option(help="Optional YAML output path for the recording."),
    ] = None,
    team: Annotated[
        list[str] | None,
        typer.Option(help=teams_help()),
    ] = None,
    window: WindowOption = True,
    quiet: QuietOption = False,
) -> None:
    """Play a level with the keyboard."""
    from simulator.run import run_play_mode

    console.set_quiet(quiet)
    configuration = with_teams(load_configuration(level), teams=team or [])
    recording_path = resolve_recording_output(
        record=record,
        recording_out_file=recording_out_file,
    )
    run_play_mode(
        configuration,
        on_step=create_recording_sink(recording_path)
        if recording_path is not None
        else None,
        level_label=Path(level).name,
        open_window=window,
    )


@app.command()
@with_controller_options
def agent(
    level: Annotated[
        Path,
        typer.Option(
            ...,
            prompt="Level to load, e.g. levels/demos/burger.yaml",
            exists=True,
            dir_okay=False,
            help="Path to a level YAML file, e.g. levels/demos/burger.yaml.",
        ),
    ],
    controller: Annotated[
        str,
        typer.Option(
            help=(
                "Registered controller to run. With --assign, this controls"
                " agents left unassigned. Run `cook controllers` for the list."
            ),
        ),
    ] = default_controller_name(),
    assign: Annotated[
        list[str] | None,
        typer.Option(
            help=(
                "Assign a controller to specific agents, for example"
                " --assign open=Alfred,Bob. Repeatable. Agents omitted from every"
                " --assign use --controller."
            ),
        ),
    ] = None,
    headless: Annotated[
        bool,
        typer.Option(help="Run the controller without launching the visualiser."),
    ] = False,
    log: Annotated[
        bool,
        typer.Option(help="Enable controller trace logging."),
    ] = False,
    record: Annotated[
        bool,
        typer.Option(help="Enable recording to a YAML file."),
    ] = False,
    recording_out_file: Annotated[
        Path | None,
        typer.Option(help="Optional YAML output path for the recording."),
    ] = None,
    result: Annotated[
        bool,
        typer.Option(help="Enable writing the simulation result to a JSON file."),
    ] = False,
    planning_budget: Annotated[
        float | None,
        typer.Option(
            min=0,
            help=(
                "Planning time in seconds for each controller for the whole run."
                " A controller stops acting when it uses its budget."
            ),
        ),
    ] = None,
    time_limit: Annotated[
        float | None,
        typer.Option(
            min=0,
            help=(
                "Wall-clock limit in seconds. The run ends when the limit is reached."
            ),
        ),
    ] = None,
    max_timesteps: Annotated[
        int | None,
        typer.Option(
            min=0,
            help="End the run when the kitchen reaches this timestep.",
        ),
    ] = None,
    end_on_orders_delivered: Annotated[
        bool,
        typer.Option(
            help=("End the run when every order has been delivered."),
        ),
    ] = False,
    end_on_budget_exhausted: Annotated[
        bool,
        typer.Option(
            help=("End the run when every controller has spent its planning budget."),
        ),
    ] = True,
    result_out_file: Annotated[
        Path | None,
        typer.Option(help="Optional JSON output path for the simulation result."),
    ] = None,
    team: Annotated[
        list[str] | None,
        typer.Option(help=teams_help()),
    ] = None,
    window: WindowOption = True,
    quiet: QuietOption = False,
    **controller_options: Any,
) -> None:
    """Run a controller on a level and report the result.

    Each registered controller adds its own options here; see
    `cook controllers`.
    """
    console.set_quiet(quiet)
    if headless and not window:
        raise typer.BadParameter(
            "--headless already means nothing is shown, so --no-window has"
            " nothing left to turn off. Use --no-window on its own to watch the"
            " run in a browser.",
            param_hint="--no-window",
        )
    configuration = with_teams(load_configuration(level), teams=team or [])
    end_conditions = build_end_conditions(
        configuration,
        headless=headless,
        time_limit=time_limit,
        max_timesteps=max_timesteps,
        planning_budget=planning_budget,
        end_on_orders_delivered=end_on_orders_delivered,
        end_on_budget_exhausted=end_on_budget_exhausted,
    )
    recording_path, result_path = resolve_run_outputs(
        record=record,
        recording_out_file=recording_out_file,
        result=result,
        result_out_file=result_out_file,
    )

    def report_result(simulation_result: SimulationResult) -> None:
        if simulation_result.error is not None:
            console.warn(
                simulation_result.error.traceback.rstrip(),
                title=ERROR_TITLES[simulation_result.error.stage],
            )
        payload = simulation_result.to_json(indent=2)
        if result_path is not None:
            result_path.write_text(payload + "\n", encoding="utf-8")
        typer.echo(payload)

    def describe(assignments: list[ControllerAssignment]) -> RunSetup:
        return describe_run(
            configuration,
            assignments,
            level=level,
            end_conditions=end_conditions,
            headless=headless,
            planning_budget=planning_budget,
        )

    described = controller_assignments(
        configuration,
        default_controller=controller,
        assignments=assign or [],
    )
    stage: ErrorStage = "import"
    try:
        import_controllers(entry.controller for entry in described)
        stage = "build"
        run = build_agent_controller(
            configuration,
            default_controller=controller,
            assignments=assign or [],
            planning_budget=planning_budget,
            options=parse_controller_options(controller_options),
        )
    except typer.BadParameter, typer.Exit:
        raise
    except RUN_ERRORS as error:
        # A controller whose code will not import, or that raises while it is
        # built, still ends in a result.
        report_result(
            Episode(load(configuration)).result(
                "error",
                setup=describe(described),
                error=RunError.from_exception(error, stage=stage),
            )
        )
        return

    run_agent_mode(
        configuration,
        run.controller,
        headless=headless,
        context=Context(log=log),
        on_step=create_recording_sink(recording_path)
        if recording_path is not None
        else None,
        end_conditions=end_conditions,
        on_result=report_result,
        setup=describe(run.assignments),
        level_label=Path(level).name,
        open_window=window,
    )


@app.command()
def replay(
    recording_path: Annotated[
        Path,
        typer.Option(
            ...,
            prompt="Recording to replay, e.g. examples/recording.yaml",
            exists=True,
            dir_okay=False,
            help=(
                "Path to a recording YAML file, e.g. examples/recording.yaml,"
                " or a gzipped one ending in .yaml.gz, as matches save."
            ),
        ),
    ],
    window: WindowOption = True,
    quiet: QuietOption = False,
) -> None:
    """Replay a recorded run one timestep at a time."""
    from simulator.run import run_replay_mode

    console.set_quiet(quiet)
    recording = load_recording(recording_path)
    run_replay_mode(
        recording,
        level_label=Path(recording_path).name,
        open_window=window,
    )


#: The competition's kitchens. A set is played in one drawn from here.
MATCH_LEVELS = Path(__file__).resolve().parent / "levels" / "3_too_many_chefs"


@app.command()
def match(
    seat: Annotated[
        list[str],
        typer.Option(
            "--seat",
            help=(
                "Who plays a seat: example, a checkout of the starter code such as"
                " ., or a controllers/open/submission folder. Give four; the first"
                " two are team A and the last two team B."
            ),
        ),
    ],
    level: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            help=(
                "A 2v2 kitchen. Left out, one is drawn from"
                " levels/3_too_many_chefs, as the competition does."
            ),
        ),
    ] = None,
    games: Annotated[
        int,
        typer.Option(min=1, help="Games in the set. The teams swap sides after each."),
    ] = GAMES,
    tick_ms: Annotated[
        int,
        typer.Option(
            min=1,
            help="How long each controller has to answer a tick, in milliseconds.",
        ),
    ] = round(TICK_SECONDS * 1000),
    max_timesteps: Annotated[
        int, typer.Option(min=1, help="Timesteps in each game.")
    ] = MAX_TIMESTEPS,
    replay_dir: Annotated[
        Path | None,
        typer.Option(help="Save each game's replay here, to watch with cook replay."),
    ] = None,
    quiet: QuietOption = False,
) -> None:
    """Play a 2v2 set between four open controllers, each in its own process."""
    import random

    from cli.match import parse_seat, play_local_set, summary

    console.set_quiet(quiet)
    if len(seat) != 4:
        raise typer.BadParameter(
            f"give four seats, not {len(seat)}", param_hint="--seat"
        )
    sources = [parse_seat(text) for text in seat]
    if level is None:
        pool = sorted(MATCH_LEVELS.glob("*.yaml"))
        if not pool:
            raise typer.BadParameter(
                f"{MATCH_LEVELS} has no kitchens", param_hint="--level"
            )
        level = random.choice(pool)
    configuration = load_configuration(level)
    try:
        teams_of(configuration)
    except MatchSetupError as error:
        raise typer.BadParameter(str(error), param_hint="--level") from None

    def echo(line: str) -> None:
        typer.echo(line, err=True)

    if not quiet:
        echo(f"Kitchen: {level}")
    report = play_local_set(
        configuration,
        sources,
        level=level.name,
        games=games,
        tick_seconds=tick_ms / 1000,
        max_timesteps=max_timesteps,
        replay_dir=replay_dir,
        echo=None if quiet else echo,
    )
    for seat_report in report.seats:
        if seat_report.error is not None:
            console.warn(
                (seat_report.error.traceback or seat_report.error.message).rstrip(),
                title=f"{seat_report.name}'S CONTROLLER CRASHED",
            )
    if not quiet:
        for line in summary(report, sources):
            echo(line)
    typer.echo(report.to_json(indent=2))


@app.command()
def controllers() -> None:
    """List the registered controllers and their options."""
    typer.echo(controller_listing())


for plugin in controller_plugins():
    if plugin.commands is not None:
        app.add_typer(plugin.commands, name=plugin.name)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
