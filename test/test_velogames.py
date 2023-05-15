from velogames.computer import Computer


def test_grand_tour() -> None:
    computer = Computer(
        config="./test/data/vuelta.toml", csv="./history/vuelta/2021.csv"
    )
    computer.compute()
    computer.publish(to_twitter=False)


def test_stage_race() -> None:
    computer = Computer(
        config="./test/data/britain.toml", csv="./history/britain/2021.csv"
    )
    computer.compute()
    computer.publish(to_twitter=False)


def test_scrap_and_compute() -> None:
    computer = Computer(config="./velogame.toml")
    computer.compute()
    computer.publish(to_twitter=False)
