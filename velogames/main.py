from velogames.computer import Computer
from velogames.scrapper import scrap, CSV


def main():
    if not CSV.exists():
        scrap()
    computer = Computer()
    computer.compute()
    computer.publish()
