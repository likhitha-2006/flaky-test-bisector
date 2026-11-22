initialized = False


def test_01_initialize():

    global initialized

    initialized = True

    assert initialized is True


def test_02_requires_initialization():

    assert initialized is True
    