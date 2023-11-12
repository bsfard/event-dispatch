import random
import threading
import time

from wrapt import synchronized

from eventdispatch import Event, post_event, register_for_events
from eventdispatch.core import map_events


def create_workers():
    # Create 3 workers (in threads).
    threads = [threading.Thread(target=run_worker, args=(i,)) for i in range(0, 4)]

    # Start all threads.
    [thread.start() for thread in threads]
    print_message('--------------------')

    # Wait for all threads to complete.
    [thread.join() for thread in threads]
    print_message('--------------------')


def run_worker(worker_id: int):
    print_message(f'Starting worker: {worker_id}')

    # Do some work.
    time.sleep(random.randint(1, 7))

    print_message(f'Finished worker: {worker_id}')

    # Notify of worker completion.
    post_event(f'worker_{worker_id}_completed', {})


def run_final_worker():
    print_message('Running final worker...')


def on_event(event: Event):
    print_message(f'Got Event: {event.name}')

    # Check for correct event, just in case, even though we only registered for this one.
    if event.name == "all_workers_completed":
        run_final_worker()


@synchronized
def print_message(msg: str):
    print(msg)


if __name__ == '__main__':
    map_events(
        [
            Event('worker_1_completed', {}),
            Event('worker_2_completed', {}),
            Event('worker_3_completed', {}),
        ],
        Event('all_workers_completed', {})
    )
    register_for_events(on_event, ['all_workers_completed'])
    create_workers()

    # Wait for final demo code to finish after last events.
    time.sleep(0.2)
