import logging
import time
from typing import Any

from eventdispatch import Event, register_for_events, unregister_from_events, post_event, NamespacedEnum

STEP_SIM_WORK_SEC = 1

logging.basicConfig(level=logging.INFO)


class WorkerEvent(NamespacedEnum):
    APP_STARTED = 'started'
    STEP1_COMPLETED = 'step1_completed'
    STEP2_COMPLETED = 'step2_completed'
    STEP3_COMPLETED = 'step3_completed'
    STEP4_COMPLETED = 'step4_completed'

    def get_namespace(self) -> str:
        return 'worker'


class Worker1:
    desired_events = [
        WorkerEvent.APP_STARTED,
        WorkerEvent.STEP2_COMPLETED,
        WorkerEvent.STEP3_COMPLETED,
    ]

    def __init__(self):
        register_for_events(self.on_event, self.desired_events)

    def on_event(self, event: Event):
        log_event(self, event)

        # Map events that occurred to action to perform.
        if event.name == WorkerEvent.APP_STARTED.namespaced_value:
            self.do_step1()

        elif event.name == WorkerEvent.STEP2_COMPLETED.namespaced_value:
            self.do_step3()

        elif event.name == WorkerEvent.STEP3_COMPLETED.namespaced_value:
            # Done (cleanup).
            unregister_from_events(self.on_event, self.desired_events)

    def do_step1(self):
        log_task(self, 'step 1')
        wait(STEP_SIM_WORK_SEC)
        post_event(WorkerEvent.STEP1_COMPLETED)

    def do_step3(self):
        log_task(self, 'step 3')
        wait(STEP_SIM_WORK_SEC)
        post_event(WorkerEvent.STEP3_COMPLETED)


class Worker2:
    desired_events = [
        WorkerEvent.STEP1_COMPLETED,
        WorkerEvent.STEP3_COMPLETED,
        WorkerEvent.STEP4_COMPLETED,
    ]

    def __init__(self):
        register_for_events(self.on_event, self.desired_events)

    def on_event(self, event: Event):
        log_event(self, event)

        # Map events that occurred to action to perform.
        if event.name == WorkerEvent.STEP1_COMPLETED.namespaced_value:
            self.do_step2()

        elif event.name == WorkerEvent.STEP3_COMPLETED.namespaced_value:
            self.do_step4()

        elif event.name == WorkerEvent.STEP4_COMPLETED.namespaced_value:
            # Done (cleanup).
            unregister_from_events(self.on_event, self.desired_events)

    def do_step2(self):
        log_task(self, 'step 2')
        wait(STEP_SIM_WORK_SEC)
        post_event(WorkerEvent.STEP2_COMPLETED)

    def do_step4(self):
        log_task(self, 'step 4')
        wait(STEP_SIM_WORK_SEC)
        post_event(WorkerEvent.STEP4_COMPLETED)


def wait(amount: float):
    time.sleep(amount)


def log_task(for_class: Any, task_name: str):
    get_logger(for_class).info(f' Doing: {task_name}\n')


def log_event(for_class: Any, event: Event):
    get_logger(for_class).info(f" Got event '{event.name}'\n{event.dict}\n")


def get_logger(cls: Any):
    return logging.getLogger(cls.__class__.__name__)
