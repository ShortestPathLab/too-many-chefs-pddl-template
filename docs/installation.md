# Installation

The [README](../README.md) provides a brief setup guide. This page explains
optional packages, planner availability by platform, and how to run the tests.

## Requirements

The project uses [uv](https://docs.astral.sh/uv/) to manage Python and its
packages. It requires Python 3.14 or newer. On first use, uv downloads a suitable Python
version if none is installed.

Commands run through uv:

```bash
uv run cook --help
```

`uv run python main.py` starts the same program as `uv run cook`, so
`uv run python main.py play ...` and `uv run cook play ...` are equivalent.

## Extras

`uv sync` installs the simulator without optional packages. Select optional
packages with `--extra`:

| Extra | What it adds |
| --- | --- |
| `fast-downward` | The Fast Downward planner. The fastest of the three, and the default when it is installed. |
| `pyperplan` | The pyperplan planner. Pure Python, so it installs on any machine, but much slower. |
| `symk` | The SymK planner, which returns the shortest plan there is. |
| `solvers` | All three planners. |
| `native` | pywebview, which opens the visualiser in a window of its own. See [The Window](modes.md#the-window). |

The PDDL controller requires at least one planner, which a plain `uv sync`
does not install. The standard installation is:

```bash
uv sync --extra fast-downward --extra native
```

`uv sync` makes the environment match the command exactly, so running it again
without an extra uninstalls that extra. Pass the same `--extra` options every
time. `uv run` only adds what is missing and never removes packages.

## Which Planner Runs Where

Fast Downward and SymK are compiled programs, published as wheels for some
platforms only. For the versions in `uv.lock`:

| Planner | Linux x86-64 | Linux ARM | macOS Apple Silicon | macOS Intel | Windows x86-64 |
| --- | --- | --- | --- | --- | --- |
| Fast Downward | yes | no | yes | yes | yes |
| SymK | yes | no | yes | no | no |
| pyperplan | yes | yes | yes | yes | yes |

On a platform without a wheel, `uv sync` stops with an error naming the
package, `up-fast-downward` or `up-symk`. Install pyperplan instead:

```bash
uv sync --extra pyperplan --extra native
```

WSL uses the Linux packages. [PDDL Solvers](solvers.md) covers how a run chooses
between the planners that are installed.

## Running the Tests

```bash
uv run pytest
```

Tests that need a planner are skipped when none is installed.
