import argparse
from pathlib import Path
import shutil

from velogames.computer import Computer
from velogames.scrapper import scrap, CSV


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=False)
    args = parser.parse_args()

    if args.csv:
        f = Path(args.csv)
        shutil.copy(f, CSV)
    else:
        if not CSV.exists():
            scrap()
    computer = Computer()
    computer.compute()
    computer.publish()
