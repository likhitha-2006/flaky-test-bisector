def test_addition():
    assert 10 + 20 == 30


def test_subtraction():
    assert 30 - 10 == 20


def test_multiplication():
    assert 5 * 4 == 20


def test_division():
    assert 20 / 5 == 4


class TestCalculator:

    def test_positive_numbers(self):
        assert 5 > 0

    def test_negative_numbers(self):
        assert -5 < 0