import time


def test_operation_timing():

    start = time.time()

    time.sleep(0.05)

    elapsed = time.time() - start

    assert elapsed >= 0.05


def test_delayed_operation():

    time.sleep(0.1)

    result = 10 + 20

    assert result == 30
    