from pathlib import Path

from velogames.computer import Computer


def test_compute() -> None:
    for cfg in Path(".").glob("*.toml"):
        if cfg.name == "pyproject.toml":
            continue
        computer = Computer(config=str(cfg))
        computer.compute()
        computer.publish(to_twitter=False)
