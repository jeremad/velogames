import argparse

from velogames.computer import Computer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=False)
    parser.add_argument("--config", required=False)
    args = parser.parse_args()

    computer = Computer(csv=args.csv, config=args.config)
    computer.compute()
    computer.publish()
