from pathlib import Path

COUNTER_FILE = Path(__file__).with_name(".flaky_counter")


def test_intermittent_failure():

    if COUNTER_FILE.exists():
        count = int(COUNTER_FILE.read_text())
    else:
        count = 0

    count += 1
    COUNTER_FILE.write_text(str(count))

    # Fails on odd runs and passes on even runs.
    assert count % 2 == 0