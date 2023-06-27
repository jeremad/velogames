import argparse

from velogames.computer import Computer
from velogames.form import post_form


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=False)
    parser.add_argument("--config", required=False)
    args = parser.parse_args()

    computer = Computer(csv=args.csv, config=args.config)
    computer.compute()
    computer.publish()


def scrap() -> None:
    Computer(csv=None)


def create_form() -> None:
    scrap()
    post_form()
