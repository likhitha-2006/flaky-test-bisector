import threading
from concurrent.futures import ThreadPoolExecutor

shared_data = []


def update_shared_data(value):

    shared_data.append(value)


def test_shared_list():

    shared_data.clear()

    with ThreadPoolExecutor(max_workers=4) as executor:

        futures = [
            executor.submit(update_shared_data, i)
            for i in range(20)
        ]

        for future in futures:
            future.result()

    assert len(shared_data) == 20


def test_thread_creation():

    thread = threading.Thread(
        target=update_shared_data,
        args=(100,)
    )

    thread.start()
    thread.join()

    assert 100 in shared_data
    