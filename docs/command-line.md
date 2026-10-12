# Command-Line Reference

Every command runs as `uv run cook <command>`, and
`uv run cook <command> --help` prints its options in the terminal.

Top-level commands:

- `play`: play a level with the keyboard
- `agent`: run a controller on a level and report the result
- `controllers`: list the registered controllers and their options
- `pddl solvers`: list the PDDL solvers
- `match`: play a set between teams of open controllers
- `replay`: replay a recorded run one timestep at a time

## `play`

```bash
uv run cook play --level levels/demos/burger.yaml
uv run cook play --level levels/demos/burger.yaml --record
uv run cook play --level levels/demos/burger.yaml --record --recording-out-file recordings/custom.yaml
```

Options:

- `--level PATH`: required path to a level YAML file
- `--record`: enable or disable recording
- `--recording-out-file PATH`: optional output path for the recording
- `--team NAME=AGENT,AGENT`: assign chefs to a team; repeatable
- `--window / --no-window`: open a separate window, or print a URL for browser access
- `--quiet` / `-q`: disable terminal status output

If `--record` is enabled and `--recording-out-file` is omitted, the app generates a UUID-based YAML filename.

## `agent`

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
- `--assign NAME=AGENT,AGENT`: assign specific chefs to a controller; repeatable.
  Unspecified chefs use `--controller`
- `--team NAME=AGENT,AGENT`: assign chefs to a team; repeatable. Unspecified chefs
  remain unassigned
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
- `--window / --no-window`: open a separate window, or print a URL for browser access; `--headless` cannot be combined with this option
- `--quiet` / `-q`: print nothing to the terminal other than the result JSON

Each registered controller adds its own options to `agent`. The PDDL
controller adds:

- `--solver NAME`: PDDL solver to use; if omitted, the first installed solver
  in the fixed priority order is selected

Headless runs with infinite orders require `--time-limit`,
`--max-timesteps`, or a `--planning-budget` that the controllers can exhaust.

## `controllers`

```bash
uv run cook controllers
```

Lists registered controllers, the default for `--controller`, and the options
each controller adds to `agent`. This command takes no options.

## `pddl solvers`

```bash
uv run cook pddl solvers
```

Lists PDDL solvers in selection order, their installation status, and the
extras required to install them. This command takes no options. Controllers
can register their own commands under their controller name.

## `match`

```bash
uv run cook match --seat . --seat . --seat example --seat example
uv run cook match --seat . --seat ../friend --seat example --seat . --level levels/3_too_many_chefs/0_full_menu.yaml --replay-dir replays
uv run cook match --level levels/1_we_can_cook/1_2_sushi_divided_3p.yaml --team red=1 --team blue=2 --team green=3 --seat ../ana --seat ../ben --seat example
```

Runs a set of games between teams of open controllers, with each seat in a
separate process. Each seat controls one chef, and every chef on a team
requires a seat. At each timestep, controllers receive the kitchen state and
have a fixed time to respond. A late response causes the chef to wait for
that tick. Teams rotate positions after each game, and the highest total
score wins. Controller output is labelled by seat; the set report is printed
as JSON.

The defaults match Part 4's competition:
two teams of two in a kitchen drawn from `levels/3_too_many_chefs`, two games
with the teams swapping sides, 300 timesteps each, and 200 ms per
controller response.

Options:

- `--seat SEAT`: controller for a seat, specified once for each chef on the kitchen's
  teams. Seats fill the teams in order, so with two teams of two the first two
  are team A and the last two team B. A seat is `example`, a checkout of the
  starter code such as `.`, or a folder whose `controller.py` defines
  `OpenController`
- `--level PATH`: a kitchen with two or more teams of the same size, or a
  folder from which to select a level with one chef per seat; if omitted, a
  level is selected from `levels/3_too_many_chefs`
- `--team NAME=AGENT,AGENT`: override the kitchen's team assignments;
  repeatable
- `--games N`: games per set; defaults to one per team, allowing each team
  to play from every position
- `--tick-ms MS`, `--max-timesteps N`: override the competition time and timestep limits
- `--replay-dir PATH`: save each game as a gzipped recording for `replay`
- `--quiet` / `-q`: print only the JSON report

## `replay`

```bash
uv run cook replay --recording-path recording.yaml
```

Options:

- `--recording-path PATH`: required path to a recording YAML file, or a
  gzipped recording ending in `.yaml.gz`, as saved by `match`
- `--window / --no-window`: open a separate window, or print a URL for browser access
- `--quiet` / `-q`: disable terminal status output
