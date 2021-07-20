from velogames.computer import Computer


def test_compute() -> None:
    computer = Computer()
    computer.compute()
    computer.publish(to_twitter=False)
