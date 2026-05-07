# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Management & Commands

This project uses [uv](https://docs.astral.sh/uv/) for dependency and environment management.

```bash
uv sync                   # Install dependencies into the virtual environment
uv run imager-selection   # Run the CLI entry point
uv run python -m imager_selection  # Run as a module
uv add <package>          # Add a new dependency
```

Python version is pinned to 3.14 (see `.python-version`).

## Architecture

The project is an imaging system selection tool. All length units are millimeters throughout the codebase.

**`src/imager_selection/imager_objects.py`** — core domain objects:

- `Camera(res_x, res_y, pp, fps_max)` — represents a camera sensor. `pp` is pixel pitch in mm. Derives sensor dimensions and sensor format (diagonal / 16) on construction.
- `Lens(focal_length, sensor_format_max, f_num, working_distance)` — represents a lens. `f_num` and `working_distance` are tuples representing ranges.
- `Imager(camera, lens)` — composite pairing of a Camera and Lens.

**`src/imager_selection/__init__.py`** — exposes the `main()` CLI entry point (registered as the `imager-selection` script in `pyproject.toml`).

Dependencies are numpy (numerical computation) and matplotlib (visualization).
