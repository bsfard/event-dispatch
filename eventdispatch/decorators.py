import functools
import threading


def singleton(cls):
    @functools.wraps(cls)
    def wrapper(*args, **kwargs):
        if not wrapper.instance:
            with wrapper.lock:
                if not wrapper.instance:
                    wrapper.instance = cls(*args, **kwargs)
        return wrapper.instance

    wrapper.instance = None
    wrapper.lock = threading.Lock()
    return wrapper
