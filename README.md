# Too Many Chefs! The Open Kitchen Challenge

Too Many Chefs is a small grid-based cooking simulator inspired by Overcooked. It lets you play a level manually, watch the built-in agent solve a level, or replay a saved recording step by step. The visualiser is a web page, shown either in a window of its own or in whichever browser you point at it.

## Install

This project uses `uv`. The PDDL controller requires a solver, which is not
included by default. Install Fast Downward with the project:

```bash
uv sync --extra fast-downward
```

Fast Downward is the default choice. It has no wheel for ARM Linux, where
`--extra pyperplan` is the portable option. One solver is enough. See
[Solvers](#solvers) for the other options.

Then run commands with:

```bash
uv run cook --help
```

Run the tests with:

```bash
uv run pytest
```

On Linux, macOS and Windows, the desktop window needs one more package:

```bash
uv sync --extra fast-downward --extra native
```

WSL does not need it. See [The Window](#the-window) for what happens without it.

## Quick Start

Play a level:

```bash
uv run cook play --level levels/demos/burger.yaml
```

Run the agent:

```bash
uv run cook agent --level levels/demos/burger.yaml
```

Replay a recording:

```bash
uv run cook replay --recording-path examples/recording.yaml
```

<!-- TODO(screenshot): Add a 1600x1000 play-mode screenshot with the HUD,
     a chef carrying an item, and at least one order visible.
     ![A burger kitchen mid-service](docs/images/play-mode.png) -->

## The Window

Modes that show a kitchen open a window and print its URL or status in the
terminal. Closing the window ends the run.

On WSL, the simulator finds Edge or Chrome on the Windows side and opens the
visualiser in app mode.

On other systems, pywebview provides the native window. Install it with the
`native` extra described under [Install](#install).

Pass `--no-window` to any visual mode, or run on a machine without a desktop,
to use a browser instead:

```
╭─ 👀 OPEN THIS LINK IN YOUR BROWSER ─────────────────────────────╮
│                                                                 │
│  The kitchen is running, but no window was opened.              │
│                                                                 │
│  Open this link in your browser to watch it:                    │
│                                                                 │
│      http://127.0.0.1:8080/                                     │
│                                                                 │
│  Why there is no window: pywebview is not installed             │
│                                                                 │
│  ● Waiting for you to open the link ...                         │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

The status indicator shows whether the browser is connected. Runs use port 8080
when it is available, then scan higher ports.

`--no-window` still serves and draws the kitchen in a browser. The `agent`
command's `--headless` option serves nothing and draws nothing.

`--quiet` disables terminal status output. On an `agent` run, only the result
JSON is written to stdout:

```bash
uv run cook agent --level levels/demos/burger.yaml --quiet > result.json
```

Use `--quiet` with a window, or use `--no-window` only when the port is known.

## Play Mode

Example:

```bash
uv run cook play --level levels/demos/burger_large.yaml
```

Play mode opens the visualiser and gives you direct control over an agent.

<!-- TODO(screenshot): Add a play-mode screenshot with the seven panels labelled.
     ![The play mode interface with each panel labelled](docs/images/play-hud-annotated.png) -->

UI overview:

- Top left shows the level, the mode, and whether the run is paused.
- Top centre is the timeline: the current timestep and how fast steps arrive.
- Top right shows the score and the number of orders delivered, and each side's running total on a kitchen split into teams.
- The left rail lists the outstanding orders and what goes into each one.
- Bottom left is the `Agents` panel: a tab per chef, then the selected chef's held item, position, facing target, and a pad lighting up whatever the last step pressed.
- Bottom centre logs the last few steps.
- Bottom right `Controls` lists the available keys.

Controls:

- `Arrow keys`: turn and move the selected agent
- `Enter`: interact with the tile in front of the agent
- `Space`: pick up, place, or combine
- `.`: wait a step without acting, for example while a station cooks
- `A`: switch to the next agent
- `M`: turn music on or off
- `H`: show or hide the interface

The `M` line in `Controls` reads `Music: on` or `Music: off`. It affects the
soundtrack only; action cues continue to play. The music keeps its place while
it is off.

If a level has multiple agents, pressing `A` cycles through them. In play mode that moves your input to the new chef as well as the panel.

To record a play session:

```bash
uv run cook play --level levels/demos/burger.yaml --record --recording-out-file recordings/burger.yaml
```

## Replay Mode

Example:

```bash
uv run cook replay --recording-path recording.yaml
```

Replay mode loads a previously recorded run and starts paused. It waits for keyboard input before playback begins.

UI overview:

- Top left shows the level and `Replay mode`.
- Top centre is the timeline. A replay knows its own length, so the bar is a real position out of the total.
- Bottom left is the `Agents` panel, showing the selected chef as of the frame on screen, including the buttons that chef pressed to produce it.
- Bottom centre logs the steps up to the current frame and no further.
- Bottom right `Controls` shows the replay hotkeys.

Controls:

- `Space`: play or pause
- `Right`: step forward one timestep
- `Left`: step back one timestep
- `A`: switch to the next agent
- `M`: turn music on or off
- `H`: show or hide the interface

The agent panel covers one chef at a time, so `A` is how you read what the others were doing on a given frame.

Replay uses recorded mutation data when available, so newer recordings preserve the same transition animations shown during live play.

## Agent Mode

Example:

```bash
uv run cook agent --level levels/demos/burger.yaml
```

Agent mode runs a controller in the visualiser. By default this is the
built-in PDDL controller; use `--controller` to select any controller from the
controller registry:

```bash
uv run cook agent --level levels/demos/burger.yaml --controller open
```

<!-- TODO(screenshot): Add an Agents panel screenshot during a plan, showing
     the selected chef, controller name, `Planning`, and a partial budget bar.
     ![The agents panel showing a controller mid-plan](docs/images/agents-panel.png) -->

Controllers are registered by name in `controllers/__init__.py` via
`controllers/registry.py`. The built-in names are:

- `pddl`: the PDDL planning controller (default)
- `open`: the open controller for Part 4's competition, in
  `controllers/open/submission/`

UI overview:

- Top left shows the level, `Agent mode`, and whether the loop is running.
- Top centre is the timeline, and top right the score and each side's total.
- Bottom left is the `Agents` panel. Alongside the selected chef's state, their side and their own share of the tips, it names the controller driving that chef, says whether it is planning, executing or idle, and shows the pad it is pressing. A run with a planning budget also shows what that controller has left of it.
- Bottom centre logs what the controller has done so far.
- Bottom right `Controls` shows the start and stop hotkey.

Visual agent mode starts stopped and waits for input from the page before the simulation begins.

Controls:

- `Space`: start or stop the agent loop
- `A`: switch to the next agent
- `M`: turn music on or off
- `H`: show or hide the interface

When a run ends, the visualiser shows a summary card with its reason, score,
deliveries, timesteps, and elapsed time. It also shows per-agent and per-team
scores when applicable. The card uses the same values as the JSON result.
Select `Quit` to exit. The card remains visible when the HUD is hidden, and
`Space` does not restart a finished run.

With several chefs under a composite controller, `A` is how you watch one of them at a time.

While running, the agent advances at the rate defined by
`VISUAL_STEP_INTERVAL_MS`. Stopping pauses the current frame.

To run without the visualiser:

```bash
uv run cook agent --level levels/demos/burger.yaml --headless
```

Headless agent mode is different from visual agent mode:

- it auto-starts immediately
- it runs as fast as possible
- it does not wait for keyboard input

To record an agent run:

```bash
uv run cook agent --level levels/demos/burger.yaml --record --recording-out-file recordings/agent.yaml
```

### Controllers

`cook controllers` lists what `--controller` can name. Each controller is a
plugin registered in `controllers/__init__.py`, and the command line learns
everything it knows about a controller from that plugin: how to build it, which
options it takes, whether it can run on this machine, what to record about it in
the result, and any commands it mounts under its own name. The command line
itself has no knowledge of PDDL or of any other controller.

A plugin is a `ControllerPlugin` from `controllers/registry.py`. The smallest
one names the controller and says how to build it:

```python
from controllers import ControllerOptions, ControllerPlugin, register_controller


def create(options: ControllerOptions) -> Controller:
    return MyController()


register_controller(
    ControllerPlugin(name="mine", summary="Does my thing.", create=create)
)
```

Options are a `ControllerOptions` subclass with one field per flag. A field
becomes `--<name>-<field>`, or the flag named in its `json_schema_extra`, and
its description is the help text. The PDDL plugin in
`controllers/pddl/plugin.py` shows the rest: a `check` that stops the run with
install instructions, a `describe` that records the chosen planner, and a
`commands` group that becomes `cook pddl solvers`.

### Teams

<!-- TODO(screenshot): Add a two-team `burger_2p.yaml` screenshot with both
     running totals visible in the top-right.
     ![A kitchen split into a red side and a blue side](docs/images/teams-score.png) -->

A kitchen can be split into teams. Repeat `--team` to assign agents:

```bash
uv run cook agent --level levels/demos/burger_2p.yaml --team red=1 --team blue=2
```

Chefs are named by badge number, which is the number the interface shows above
each of them and the number the action log calls them by. A level that gives its
chefs names in `legend.agents` can use those instead. Play mode takes `--team`
too, so two people at one keyboard can cook against each other.

Teams and controllers are independent. A controller can drive one or more
teams, and a team can be split across controllers. Scores still belong to the
agent that earned them. To run a controller per side:

```bash
uv run cook agent --level levels/2_overcooked/0_black_forest_cake_parallel_stations_4p.yaml \
  --team red=A,B --team blue=C,D \
  --assign pddl=A,B --assign open=C,D
```

That example uses a level that names its chefs, because `--assign` only takes
names. `--team` takes badge numbers as well, so a level that names nothing can
still be split into sides, but its chefs cannot be handed to separate
controllers until the level gives them names.

A level can define its own teams:

```yaml
teams:
  red: [1, 2]
  blue: [3, 4]
```

If any team is named on the command line, the command-line rosters replace the
level rosters. An agent omitted from every roster is unassigned. Its score
counts for the kitchen but not for a team.

The known colours are red, blue, green, yellow, purple and orange, and they are
what a side is drawn in. Any other name works and comes out gray.

While a run is active, each team total appears beside the kitchen total in the
top-right. The agent panel shows the selected agent's team.
The ending card lists the sides, and calls the winner or says it was a draw.

### Planning Budget

You can put the controllers on a clock. `--planning-budget` gives each of them a
number of seconds of thinking time for the whole run, and one that has spent its
share is not allowed to act again:

```bash
uv run cook agent --level levels/demos/burger.yaml --headless --planning-budget 30
```

The budget belongs to the controller, not to an agent. A controller driving four
agents shares one 30-second budget across them. With `--assign`, each named
controller gets a separate budget.

The clock charges time spent in `get_actions` and time spent by a background
worker after that call returns. The PDDL controller searches in a subprocess,
so both intervals count. The controller starts those workers before the run
begins, so starting them counts against neither the budget nor `--time-limit`.

If a controller exceeds its budget, its current action is kept and later calls
return no actions. The agent inspector shows `Out of time`, and the budget bar
updates during a search.

### Solvers

The PDDL controller plans by handing a domain and a problem to a solver. None of
them ships with the project, so at least one has to be installed before anything
can plan. There are three:

| Name | Installs with | Notes |
| --- | --- | --- |
| `fast-downward` | `uv sync --extra fast-downward` | Satisficing search. The fastest of the three, and the default when it is installed. |
| `pyperplan` | `uv sync --extra pyperplan` | Pure Python, so it installs on any machine. Much slower than the compiled planners. |
| `symk` | `uv sync --extra symk` | Symbolic bidirectional search, so the plan it returns is the shortest one there is. |

`uv sync --extra solvers` installs all three at once. Neither Fast Downward nor
SymK publishes a wheel for ARM Linux, and SymK publishes none for Windows;
pyperplan runs anywhere.

If no planner is installed, the run stops before it starts and lists the
commands needed to install one.

To list the installed solvers:

```bash
uv run cook pddl solvers
```

Left alone, a run tries them in the order above and plans with the first one
installed here. Name one with `--solver` to override that:

```bash
uv run cook agent --level levels/demos/burger.yaml --solver symk
```

Naming an unavailable solver stops the run and shows the required extra. Every
PDDL controller in the run uses the selected solver. Controllers that do not use
PDDL ignore this option. `--solver` belongs to the PDDL controller rather than
to the command line itself; see [Controllers](#controllers) for how a
controller adds options of its own.

Writing a solver of your own means subclassing `Solver` in
`controllers/pddl/solvers/base.py` and registering it with `register_solver`.
Adapters for the three above live beside it, and the shortest is
`controllers/pddl/solvers/pyperplan_solver.py`.

### End Conditions and Results

Without an explicit condition, an agent run ends when its controller reports
that it is finished. Infinite-order levels do not reach that state. These
options add other end conditions and can be combined:

- `--time-limit SECONDS` ends it on the wall clock.
- `--max-timesteps N` ends it at timestep N. The visualiser shows the timeline
  as a fraction of N.
- `--end-on-orders-delivered` ends it once every order has been delivered. An
  expired order does not count as delivered.
- `--end-on-budget-exhausted` ends it once every controller has spent its
  planning budget. It is on by default, because a kitchen where nobody is
  allowed to plan never takes another step. If you turn it off with
  `--no-end-on-budget-exhausted`, give the run a `--time-limit` to stop it
  instead.

Headless runs of infinite-order levels require `--time-limit`,
`--max-timesteps`, or a planning budget that can be exhausted.

<!-- TODO(screenshot): Add an ending-card screenshot over the dimmed kitchen,
     showing the headline, score, and per-chef breakdown.
     ![The card shown at the end of a run](docs/images/ending-card.png) -->

A headless run stops on the spot: the condition is checked before the controller
is asked for anything, so nothing else happens after the one that ends it. A
visual run stops the kitchen and shows the ending card described above.

Either way, agent mode prints a JSON simulation result and can also write it to a
file with `--result-out-file`:

```json
{
  "run": {
    "level": "levels/demos/burger_2p.yaml",
    "controllers": [
      {
        "controller": "pddl",
        "agents": [],
        "details": { "solver": "fast-downward", "solver_selection": "automatic" }
      }
    ],
    "teams": {
      "red": ["4e39"],
      "blue": ["7f6a"]
    },
    "headless": true,
    "planning_budget_seconds": null,
    "end_conditions": {
      "time_limit_seconds": 30.0,
      "max_timesteps": null,
      "end_on_orders_delivered": false,
      "end_on_budget_exhausted": true
    }
  },
  "reason": "completed",
  "score": 52,
  "score_by_agent": {
    "4e39": 4,
    "7f6a": 48
  },
  "score_by_team": {
    "red": 4,
    "blue": 48
  },
  "timesteps": 13,
  "orders_delivered": 1,
  "orders_remaining": 0,
  "elapsed_seconds": 2.6,
  "error": null
}
```

`run` records what the run was asked to do, so a result file can be read
without the command that produced it. `level` is the path as it was given.
`controllers` lists each controller and the chefs it owns; an entry with an
empty `agents` list is the `--controller` default, which takes whatever
`--assign` left over. `details` is whatever that controller chose to record
about itself. For the PDDL controller, `solver` names the planner that ran and
`solver_selection` says where that name came from: `named` if `--solver` chose
it, `automatic` if the run took the first installed solver in priority order.
The open controller records nothing. `teams`, `headless`,
`planning_budget_seconds`, and `end_conditions` repeat the options the run
started with. `run` is `null` for a run driven from code rather than from the
command line.

`reason` is `completed` when the controller has no more actions and no orders
remain. It is `gave_up` when the controller has no more actions but orders
remain. Use this value to distinguish a completed service from a planner that
found no plan. `stopped` means that a visual session was closed early. Other
values identify the ending condition: `time_limit`, `max_timesteps`,
`orders_delivered`, or `planning_budget_exhausted`. If conditions match on the
same step, the first matching option wins.

`error` means an exception ended the run. A controller may have raised one, or
the planner may have rejected the PDDL it was given. The result then carries an
`error` object with the exception's `type`, `message` and `traceback`; for an
exception from a planning worker, the traceback includes the worker's own. Its
`stage` says when the exception came: `import` when the controller's code would
not import, `build` when the controller raised while it was being built, and
`run` once the run had started. The PDDL controller imports the students'
modules only when a run uses it, so a module with a syntax error ends that run
with `stage` set to `import` and leaves other controllers and commands working.
What the run did before the error still counts, so `score` and `timesteps` are
what it had reached. Without `--quiet` the traceback is printed as well. The
command exits with status 0 whenever it prints a result, so a script that reads
the JSON handles a failed run the same way as any other.

`score` is the kitchen total. `score_by_agent` splits it by agent id in badge
order and includes agents with no score.

`score_by_team` groups the score by team. It is empty when no teams are
configured. Team totals equal the kitchen total only when every agent belongs
to a team. An unassigned agent contributes to the kitchen total only.

## Command Line Options

Top-level commands:

- `play`
- `agent`
- `replay`

### `play`

```bash
uv run cook play --level levels/demos/burger.yaml
uv run cook play --level levels/demos/burger.yaml --record
uv run cook play --level levels/demos/burger.yaml --record --recording-out-file recordings/custom.yaml
```

Options:

- `--level PATH`: required path to a level YAML file
- `--record`: enable or disable recording
- `--recording-out-file PATH`: optional output path for the recording
- `--team NAME=AGENT,AGENT`: put chefs on a side; repeatable
- `--window / --no-window`: open a window of its own, or print a URL to open in
  a browser
- `--quiet` / `-q`: disable terminal status output

If `--record` is enabled and `--recording-out-file` is omitted, the app generates a UUID-based YAML filename.

### `agent`

```bash
uv run cook agent --level levels/demos/burger.yaml
uv run cook agent --level levels/demos/burger.yaml --controller open
uv run cook agent --level levels/demos/burger.yaml --headless --time-limit 30
uv run cook agent --level levels/demos/burger.yaml --headless --planning-budget 30 --max-timesteps 400
uv run cook agent --level levels/demos/burger.yaml --headless --end-on-orders-delivered
uv run cook agent --level levels/demos/burger.yaml --record --recording-out-file recordings/agent.yaml
uv run cook agent --level levels/demos/burger_2p.yaml --team red=1 --team blue=2
```

Options:

- `--level PATH`: required path to a level YAML file
- `--controller NAME`: registered controller to run (default `pddl`)
- `--assign NAME=AGENT,AGENT`: give a controller specific chefs; repeatable, and
  chefs left out fall back to `--controller`
- `--team NAME=AGENT,AGENT`: put chefs on a side; repeatable, and chefs left out
  are on no side
- `--headless / --no-headless`: run the controller without launching the visualiser
- `--planning-budget SECONDS`: planning time for each controller for the whole
  run; a controller that exhausts it stops acting
- `--time-limit SECONDS`: wall-clock limit; the run is terminated and results
  are reported once exceeded
- `--max-timesteps N`: end the run once the kitchen reaches timestep N
- `--end-on-orders-delivered / --no-end-on-orders-delivered`: end the run once
  every order has been delivered (default off)
- `--end-on-budget-exhausted / --no-end-on-budget-exhausted`: end the run once
  every controller has spent its planning budget (default on)
- `--result / --no-result`: write the simulation result to a JSON file
- `--result-out-file PATH`: optional JSON output path for the simulation result
- `--record / --no-record`: enable or disable recording
- `--recording-out-file PATH`: optional output path for the recording
- `--log / --no-log`: enable controller trace logging
- `--window / --no-window`: open a window of its own, or print a URL to open in
  a browser; `--headless` already shows nothing, so the two do not go together
- `--quiet` / `-q`: print nothing to the terminal other than the result JSON

Each registered controller adds its own options to `agent`. The PDDL
controller adds:

- `--solver NAME`: the PDDL solver to plan with; left out, the solvers are
  tried in a fixed order and the first one installed here does the planning

A headless run of a level whose orders never run out needs one of
`--time-limit`, `--max-timesteps`, or a `--planning-budget` the controllers can
run out of.

### `controllers`

```bash
uv run cook controllers
```

Lists the registered controllers, which one `--controller` picks by default,
and the options each one adds to `agent`. Takes no options.

### `pddl solvers`

```bash
uv run cook pddl solvers
```

Lists the PDDL solvers in the order one would be chosen, saying which are
installed here and which extra installs the rest. Takes no options. A
controller can mount commands of its own under its name this way.

### `match`

```bash
uv run cook match --seat . --seat . --seat example --seat example
uv run cook match --seat . --seat ../friend --seat example --seat . --level levels/3_too_many_chefs/3_burgers.yaml --replay-dir replays
```

Plays a 2v2 set between four open controllers, each in its own process, the
way Part 4's competition does: two games in one kitchen with the teams swapping
sides, 300 timesteps each, and 200 ms for each controller to answer a tick. A
late answer leaves that chef standing still for the tick. What each controller
prints is marked with its seat, and the set's report is printed as JSON.

Options:

- `--seat SEAT`: who plays a seat, given four times; the first two are team A
  and the last two team B. A seat is `example`, a checkout of the starter code
  such as `.`, or a `controllers/open/submission` folder
- `--level PATH`: the kitchen; left out, one is drawn from
  `levels/3_too_many_chefs`
- `--games N`, `--tick-ms MS`, `--max-timesteps N`: try other limits than the
  competition's
- `--replay-dir PATH`: save each game as a gzipped recording for `replay`
- `--quiet` / `-q`: print only the JSON report

### `replay`

```bash
uv run cook replay --recording-path recording.yaml
```

Options:

- `--recording-path PATH`: required path to a recording YAML file, or a
  gzipped one ending in `.yaml.gz` as `match` saves
- `--window / --no-window`: open a window of its own, or print a URL to open in
  a browser
- `--quiet` / `-q`: disable terminal status output


## Writing Custom Levels

Level files are YAML documents with these main sections:

- `name`: optional display name; the UI falls back to the filename
- `description`: optional short description shown beneath the name
- `layout`: the map grid
- `state`: current orders and other initial runtime state
- `legend`: what each layout symbol means
- `recipes`: cook and combine recipes
- `bounds`: optional explicit bounds override
- `rules`: optional order visibility, ordering, time limits, and timed cooking
- `scoring`: optional rewards for order progress and delivery
- `soundtrack`: optional music the level is cooked to

Names and descriptions may be omitted or set to `null`. Blank names also use
the filename; blank descriptions are hidden. Metadata is retained in recordings
so replays show the same level details.

```yaml
name: Burger kitchen
description: Grill patties, slice cheese, and assemble two kinds of burger.
```

### Minimal Structure

```yaml
layout: |-
  | - | - | - | * |
  | - | 1 | B | - |
  | - | - | - | - |

state:
  orders:
    - catalog/food/hamburger
appearance:
  floor_type: -1
  wall_type: -1
  background: 5
legend:
  counters:
    - symbol: "-"
  storages:
    - symbol: B
      food_name: catalog/food/bun
  deliveries:
    - symbol: "*"
  agents:
    - symbol: "1"
      orientation: s
  foods:
    - name: catalog/food/bun

recipes:
  cook: []
  combine: []
```

### Layout

<!-- TODO(screenshot): Add a two-pane example with the raw `layout:` block and
     the rendered kitchen, connected by arrows from symbols to entities.
     ![A level layout string and the kitchen it renders as](docs/images/layout-to-kitchen.png) -->

The `layout` is a grid. This project commonly uses cell-delimited rows like this:

```yaml
layout: |-
  | - | 1 |   | * |
  | - | B | M | X |
```

Each cell can contain:

- a single symbol like `1`, `B`, or `*`
- multiple symbols in the same cell like `-p` or `/-`
- spaces for an empty cell

Examples from the existing levels:

- `-` means a counter
- `1` or `2` means an agent
- `B`, `M`, `C` can be ingredient storages
- `*` is a delivery tile
- `X` is a bin
- `D` is a plate dispenser
- `S` is a sink
- `/-` means a cutboard on top of a counter
- `VR` means a stove and pan in the same cell
- `-p` means a plate on a counter

When multiple symbols appear in one cell, the loader places them together and automatically attaches portable items to counters or equipment when appropriate.

### Legend

The `legend` defines what symbols in the layout mean. Supported sections are:

- `agents`
- `bins`
- `counters`
- `deliveries`
- `equipment`
- `plates`
- `plate_dispensers`
- `sinks`
- `foods`
- `storages`

Examples:

```yaml
appearance:
  floor_type: -1
  wall_type: -1
  background: 5
legend:
  counters:
    - symbol: "-"
  equipment:
    - symbol: /
      name: catalog/equipment/cutboard
    - symbol: V
      name: catalog/equipment/stove
    - symbol: R
      name: catalog/equipment/pan
  storages:
    - symbol: B
      food_name: catalog/food/bun
  deliveries:
    - symbol: "*"
  agents:
    - symbol: "1"
      orientation: s
```

Notes:

- Layout symbols must be a single character.
- Symbols must be unique across the full legend.
- Agents support `orientation: n | s | e | w`.
- Some entries can define `held_item` if you want an object to start already carrying food.
- Equipment can define flags like `requires`, `can_pick_up`, and `can_process_food`, and the `cook_time` and `cooks_by_itself` settings described under [Timed Cooking](#timed-cooking).
- Equipment can define `sound`, the clip played when it works on food. Equipment that leaves it out gets a generic one.

### Plates and Washing Up

A dish goes out on a plate, so every level has to put plates somewhere. Scatter
them around the kitchen with `plates`, keep a stack in one place with
`plate_dispensers`, or do both.

```yaml
legend:
  plates:
    - symbol: p
  plate_dispensers:
    - symbol: D
      plate_count: 3
```

A dispenser holds a finite stack. Delivering a dish returns its plate to the
first dispenser in the level, so the supply is conserved and a kitchen whose
orders never run out never runs out of plates either. `infinite_supply: true`
skips the bookkeeping: the dispenser always has a plate and ignores the ones
that come back.

Set `returns_dirty: true` and plates come back off the pass used:

```yaml
legend:
  plate_dispensers:
    - symbol: D
      plate_count: 3
      returns_dirty: true
  sinks:
    - symbol: S
```

Used plates cannot hold food. An agent must carry a used plate to a sink and
wash it. A dispenser returns clean plates before used plates. If a level dirties
plates without providing a sink, it can serve only `plate_count` dishes.

Two settings support starting a level mid-service: `dirty_plate_count` starts a
dispenser with used plates already in it,
and `dirty: true` on a `plates` entry leaves a used one on a counter.

The interact key washes when a chef is facing a sink. In a plan, that is a
`Wash` mutation at the sink's location. See
`levels/demos/burger_washing_up.yaml`.

### Station Sounds

`sound` takes a filename, a list of interchangeable takes, or the long form when you want to set the level and the pitch spread too. Paths are relative to `assets/audio`.

```yaml
equipment:
  - symbol: /
    name: catalog/equipment/cutboard
    sound: chop.ogg
  - symbol: V
    name: catalog/equipment/stove
    sound: [metalPot2.ogg, metalPot3.ogg]
  - symbol: O
    name: catalog/equipment/oven
    sound:
      clips: [doorClose_1.ogg, doorClose_4.ogg]
      gain: 0.4
      jitter: 0.04
```

Give a station several takes where possible. The browser avoids repeating the
same clip twice in a row. `jitter` detunes each play by up to the specified
fraction.

A level that sets `sound` on a piece of equipment overrides whatever `catalog/equipment.yaml` says for it.

### Soundtrack

`soundtrack` names the level music. Tracks are mp3 files in
`assets/audio/soundtrack` and are referenced by file stem.

```yaml
soundtrack:
  - we-can-cook-together-side-a
  - we-can-cook-together-side-b
```

One name is shorthand for a one-track playlist. The long form also sets the
music volume:

```yaml
soundtrack: low-key-cooking-side-a
```

```yaml
soundtrack:
  tracks: [turning-up-the-heat, galaxy-famous-chef]
  gain: 0.25
```

The visualiser plays tracks in order and loops the playlist. Music starts on the
first keypress because browsers block autoplay. Pressing `M` turns the music off
without pausing playback, so turning it back on resumes at the same place.

`gain` defaults below the cue levels. A level without `soundtrack` uses cues
only.

The shipped levels use playlists by difficulty. `low-key-cooking` covers the
single-chef kitchens in `0_i_can_cook`, `we-can-cook-together` covers the
co-op kitchens in `1_we_can_cook`, and `digital-kitchen` covers both. The
remaining playlists are used by `2_overcooked`, the eight-chef kitchen, and
other difficult levels. `tests/test_soundtrack.py` checks that every playlist
name has a corresponding file.

### Foods and Recipes

`legend.foods` must include every food item used anywhere in the level, not just the raw ingredients. That includes:

- order outputs
- storage outputs
- recipe ingredients
- intermediate recipe results
- held items placed on agents, counters, equipment, or plates

Example:

```yaml
legend:
  foods:
    - name: catalog/food/cheese
    - name: catalog/food/sliced_cheese
    - name: catalog/food/bun
    - name: catalog/food/meat
    - name: catalog/food/grilled_meat
    - name: catalog/food/hamburger

recipes:
  cook:
    - ingredient: catalog/food/meat
      with: catalog/equipment/pan
      to_make: catalog/food/grilled_meat
  combine:
    - ingredients: [catalog/food/bun, catalog/food/grilled_meat]
      to_make: catalog/food/hamburger
```

If a referenced food is missing from `legend.foods`, loading the level will fail validation.

### Illegal Recipes

By default a kitchen only does what the recipes describe. Put bread in the pan
or press two buns together and the kitchen refuses, so nothing moves. A level
can lift that:

```yaml
rules:
  allow_illegal_recipes: true
```

With the rule on, any station that cooks something accepts any ingredient, and
any two items can be combined on a counter, in a station, or on a plate.
Undefined recipe results become either `catalog/food/dubious_food` or
`catalog/food/rock_hard_food`. Neither can be delivered or scored. Discard them
in a bin.

Which of the two appears is drawn from the ingredients and the timestep, so a
recording replays into the same garbage it was recorded with.

Two cases remain invalid. A station with no cook recipe in the level refuses
ingredients, and a plate is not a cooking station. Pressing the cook key on a
plated dish has no effect.

The two garbage items are provided by the rule, so
`legend.foods` does not have to declare them. Declaring one anyway overrides its
art. See `levels/demos/burger_anything_goes.yaml`.

### Timed Cooking

By default every station cooks with one press of interact. A level can give
each station its own cooking time instead:

```yaml
rules:
  timed_cooking: true
```

Under this rule, each station follows two settings from its equipment
definition. `cook_time` is how long food takes there. `cooks_by_itself` says
whether the station counts that time down on its own or a chef has to press
interact once per step of it, the way you chop in Overcooked. The catalog gives
the usual stations these defaults:

| Station | `cook_time` | `cooks_by_itself` |
| --- | --- | --- |
| Cutboard | 3 | no |
| Mixing bowl | 3 | yes |
| Pan | 4 | yes |
| Deep fryer | 5 | yes |
| Pot | 6 | yes |
| Oven | 8 | yes |

A station that sets neither cooks with one press, as it does without the rule.
A level can change a station in its legend, like any other catalog field:

```yaml
legend:
  equipment:
    - symbol: O
      name: catalog/equipment/oven
      cook_time: 12 # a slow oven
    - symbol: R
      name: catalog/equipment/pan
      cooks_by_itself: false # a pan the chef has to work
```

Stations that share a name must agree on `cooks_by_itself`, because a planner
treats them as one kind of equipment. Their cook times may differ.

A station that cooks by itself starts as soon as food it has a recipe for goes
in. Food put in during one step is ready `cook_time` steps later, the chef who
put it in gets the reward for preparing it, and pressing interact there does
nothing. For a station cooked by hand, the chef who makes the last press gets
the reward. A bar above either kind of station shows how far along the food is.

Some details:

- Progress belongs to the food in the station. Chops stay on the board while
  the chef is away, but taking the food out, or adding an ingredient to it,
  starts it over.
- A station cooks only while it stands on the station it needs. A pan lifted off
  the stove keeps its progress and carries on when it goes back on a stove.
- If the result of a station that cooks by itself has its own recipe there, it
  keeps cooking. A level can use this for burning, with a recipe that turns
  `grilled_meat` in a pan into burnt meat. With illegal recipes on, any food left
  in such a station after it finishes turns into garbage.
- Time keeps passing while food cooks by itself. In agent mode the simulator
  steps even when the controller returns no actions, unless the controller is
  still planning. In play mode, press `.` to wait a step.

See `levels/demos/burger_timed.yaml`, where the pan grills by itself and the
cheese takes three chops.

### Orders

Orders live under `state.orders`:

```yaml
state:
  orders:
    - catalog/food/hamburger
    - catalog/food/cheeseburger
```

Optional rules control delivery order, visibility, and timing:

```yaml
rules:
  strict_ordering: false
  order_reveal: sequential # all | sequential
  default_order_time_limit: 20 # timesteps after each order is revealed
```

Levels can also enable infinite mode, where orders never run out. The listed
`state.orders` become a pool of order templates: whenever an order is
delivered or expires, a replacement is drawn from the pool deterministically
based on `order_seed`:

```yaml
rules:
  infinite_orders: true
  order_seed: 0 # change for a different deterministic order sequence
  max_visible_orders: 2 # defaults to the number of listed orders
```

Infinite mode ignores `order_reveal` and requires at least one entry in
`state.orders`. An infinite level never finishes on its own, so headless agent
runs must set `--time-limit`. See `levels/demos/burger_infinite.yaml` for an
example.

Optional scoring rewards completed orders and useful recipe progress:

```yaml
scoring:
  default_order_reward: 50
  retrieve_order_component_reward: 1
  produce_order_component_reward: 1
  produce_ordered_item_reward: 1
```

`default_order_reward` is what an order pays when it does not name its own
`reward`.

An order component is an ingredient or intermediate recipe output that
contributes to a currently visible order.

A food pays its progress reward only while fewer have been paid than the
visible orders need. Fetching a second tomato for one salad earns nothing, but
two salad orders pay for two tomatoes. The count is not tied to a particular
order: when an order is served or expires, it gives back its share, so a
tomato fetched for the next order pays again. In a kitchen split into teams,
each team keeps its own count, so one side's progress never uses up the
other's rewards.

### Catalog Defaults

If your project has a nearby `catalog/food.yaml` or `catalog/equipment.yaml`, level definitions can inherit defaults from those files. The loader searches upward from the level file to find a `catalog/` directory.

## Example Levels

The [demo collection](levels/demos/README.md) covers recipes, team sizes,
divided kitchens, prepared ingredients, finite supplies, order rules, and
washing up. Start with `levels/demos/coconut_juice.yaml` or
`levels/demos/burger.yaml`; see the collection index for each level's purpose.

The graded practice sets live in their own folders, each with a README:
`levels/0_i_can_cook` for solo kitchens, `levels/1_we_can_cook` for two chefs
and up, and `levels/2_overcooked` for the hard ones. `levels/3_too_many_chefs`
holds the symmetric 2v2 kitchens Part 4's competition is played in.

## Licence

MIT. See [LICENSE](LICENSE).
