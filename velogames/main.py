import argparse

from velogames.computer import Computer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=False)
    args = parser.parse_args()

    computer = Computer(args.csv)
    computer.compute()
    computer.publish()
