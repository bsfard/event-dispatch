import time
from concurrent.futures import ThreadPoolExecutor

from eventdispatch.decorators import singleton


def test_singleton__when_called_from_multiple_threads():
    init_count = 0

    @singleton
    class TestSingleton:
        def __init__(self):
            nonlocal init_count
            time.sleep(0.01)
            init_count += 1

    with ThreadPoolExecutor(max_workers=20) as executor:
        instances = list(executor.map(lambda _: TestSingleton(), range(20)))

    assert init_count == 1
    assert len({id(instance) for instance in instances}) == 1
