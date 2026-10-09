# PDDL Solvers

The PDDL controller submits a domain and a problem to a solver. Solvers are
installed separately; at least one is required for PDDL planning. Three solvers
are supported:

| Name | Installs with | Notes |
| --- | --- | --- |
| `fast-downward` | `uv sync --extra fast-downward` | Satisficing search. The fastest of the three, and the default when it is installed. |
| `pyperplan` | `uv sync --extra pyperplan` | Pure Python, so it installs on any machine. Much slower than the compiled planners. |
| `symk` | `uv sync --extra symk` | Symbolic bidirectional search, so the plan it returns is the shortest one there is. |

`uv sync --extra solvers` installs all three at once. Fast Downward and SymK
publish wheels for some platforms only, and `uv sync` fails on the others; see
[Which Planner Runs Where](installation.md#which-planner-runs-where).
pyperplan runs anywhere.

If no planner is installed, the run is rejected before execution and the
required installation commands are displayed.

To list the installed solvers:

```bash
uv run cook pddl solvers
```

By default, the run selects the first installed solver in the order above.
Use `--solver` to select a specific solver:

```bash
uv run cook agent --level levels/demos/burger.yaml --solver symk
```

Naming an unavailable solver stops the run and shows the required extra. Every
PDDL controller in the run uses the selected solver. Controllers that do not use
PDDL ignore this option. `--solver` belongs to the PDDL controller rather than
to the command line itself; see
[Controller Plugins](agent-runs.md#controller-plugins) for how a controller
adds options of its own.

To add a solver, subclass `Solver` in
`controllers/pddl/solvers/base.py` and register it with `register_solver`.
The existing adapters are in the same directory; the shortest is
`controllers/pddl/solvers/pyperplan_solver.py`.
