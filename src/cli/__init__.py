"""CLI 兼容入口

用于 project.scripts = "cli:cli" 的入口，转发到项目根目录的 cli.py。
"""

from importlib import util
from pathlib import Path


def _load_root_cli():
    root_dir = Path(__file__).resolve().parents[2]
    cli_path = root_dir / "cli.py"
    spec = util.spec_from_file_location("diting_root_cli", cli_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load CLI module from {cli_path}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_root_cli = _load_root_cli()
cli = _root_cli.cli

__all__ = ["cli"]
