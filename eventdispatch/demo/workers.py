import json
import logging
import time

from eventdispatch import Event, register_for_events, unregister_from_events, post_event, NamespacedEnum, Properties, \
    map_events

STEP_SIM_WORK_SEC = 1


class WorkerEvent(NamespacedEnum):
    APP_STARTED = 'started'
    STEP1_COMPLETED = 'step1_completed'
    STEP2_COMPLETED = 'step2_completed'
    STEP3_COMPLETED = 'step3_completed'
    STEP4_COMPLETED = 'step4_completed'
    ALL_STEPS_COMPLETED = 'all_steps_completed'

    def get_namespace(self) -> str:
        return 'worker'


class Worker:
    def __init__(self, events_to_watch: [WorkerEvent]):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.events_to_watch = events_to_watch
        self.is_pretty_print = Properties().has('CLIENT_LOGGING_PRETTY_PRINT') and \
                               Properties().get('CLIENT_LOGGING_PRETTY_PRINT')

        register_for_events(self.on_event, self.events_to_watch)

    def on_event(self, event: Event):
        self.log_event(event)

    @staticmethod
    def wait(amount: float):
        time.sleep(amount)

    def log_task(self, task_name: str):
        self.logger.info(f'Doing: {task_name}\n')

    def log_event(self, event: Event):
        if self.is_pretty_print:
            payload = json.dumps(event.dict, indent=2)
        else:
            payload = event.dict
        self.logger.info(f"Got event '{event.name}'\n{payload}\n")

    def unregister(self):
        unregister_from_events(self.on_event, self.events_to_watch)


class Worker1(Worker):
    events_to_watch = [
        WorkerEvent.APP_STARTED,
        WorkerEvent.STEP2_COMPLETED,
        WorkerEvent.STEP3_COMPLETED,
    ]

    def __init__(self):
        super().__init__(self.events_to_watch)

    def on_event(self, event: Event):
        super().on_event(event)

        # Map events that occurred to action to perform.
        if event.name == WorkerEvent.APP_STARTED.namespaced_value:
            self.do_step1()

        elif event.name == WorkerEvent.STEP2_COMPLETED.namespaced_value:
            self.do_step3()

        elif event.name == WorkerEvent.STEP3_COMPLETED.namespaced_value:
            # Done (cleanup).
            self.unregister()

    def do_step1(self):
        self.log_task('step 1')
        self.wait(STEP_SIM_WORK_SEC)
        post_event(WorkerEvent.STEP1_COMPLETED, {'id': 10})

    def do_step3(self):
        self.log_task('step 3')
        self.wait(STEP_SIM_WORK_SEC)
        post_event(WorkerEvent.STEP3_COMPLETED)


class Worker2(Worker):
    events_to_watch = [
        WorkerEvent.STEP1_COMPLETED,
        WorkerEvent.STEP3_COMPLETED,
        WorkerEvent.STEP4_COMPLETED,
    ]

    def __init__(self):
        super().__init__(self.events_to_watch)

    def on_event(self, event: Event):
        super().on_event(event)

        # Map events that occurred to action to perform.
        if event.name == WorkerEvent.STEP1_COMPLETED.namespaced_value:
            self.do_step2()

        elif event.name == WorkerEvent.STEP3_COMPLETED.namespaced_value:
            self.do_step4()

        elif event.name == WorkerEvent.STEP4_COMPLETED.namespaced_value:
            # Done (cleanup).
            self.unregister()

    def do_step2(self):
        self.log_task('step 2')
        self.wait(STEP_SIM_WORK_SEC)
        post_event(WorkerEvent.STEP2_COMPLETED)

    def do_step4(self):
        self.log_task('step 4')
        self.wait(STEP_SIM_WORK_SEC)
        post_event(WorkerEvent.STEP4_COMPLETED, {'age': 25})


class Worker3(Worker):
    events_to_watch = [
        WorkerEvent.ALL_STEPS_COMPLETED
    ]

    def __init__(self):
        super().__init__(self.events_to_watch)

        super().__init__(self.events_to_watch)

        event_map_key = map_events(
            events_to_map=[
                Event(WorkerEvent.STEP1_COMPLETED, {'id': 10}),
                Event(WorkerEvent.STEP2_COMPLETED),
                Event(WorkerEvent.STEP3_COMPLETED),
                Event(WorkerEvent.STEP4_COMPLETED, {'age': 25})
            ],
            event_to_post=Event(WorkerEvent.ALL_STEPS_COMPLETED, {'message': 'hello'}),
            ignore_if_exists=True
        )
        self.logger.info(f'Event Map Key: {event_map_key}')

    def on_event(self, event: Event):
        super().on_event(event)

        if event.name == WorkerEvent.ALL_STEPS_COMPLETED.namespaced_value:
            # Done (cleanup).
            self.unregister()
