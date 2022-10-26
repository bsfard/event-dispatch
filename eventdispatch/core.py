import json
import logging
import threading
import time
import traceback
from collections import deque
from typing import Callable


class NotifiableError(Exception):
    """Base error that posts event for this error"""

    def __init__(self, message: str, error: str, payload: dict, exception: traceback = None):
        # Check if subclass provided an error already, which could be a sub-error type.
        if 'error' not in payload:
            payload['error'] = error

        if exception:
            payload['stacktrace'] = ''.join(
                traceback.format_exception(etype=type(exception), value=exception, tb=exception.__traceback__))

        super().__init__(message)
        EventDispatch().post_event(error, payload)


class Data:
    def __init__(self, data: dict):
        if data is None:
            raise InvalidDataError()
        self.__data = data

    def get(self, key: str, data: dict = None):
        data = data if data else self.__data
        try:
            return data[key]
        except KeyError:
            raise MissingKeyError(key, data)

    @property
    def raw(self) -> dict:
        return self.__data

    @property
    def json(self) -> str:
        return json.dumps(self.__data)


class InvalidDataError(NotifiableError):
    def __init__(self):
        message = f"Cannot create data object from 'None' data input"
        error = 'invalid_data_input'
        payload = {}
        super().__init__(message, error, payload)


class MissingKeyError(NotifiableError):
    def __init__(self, key: str, data: dict):
        message = f"Could not find key '{key}' within data:\n{data}."
        error = 'missing_key'
        payload = {
            'key': key,
            'data': data
        }
        super().__init__(message, error, payload)


class Event(Data):
    __lock = threading.Lock()
    __id = 0

    def __init__(self, name: str, payload: dict):
        super(Event, self).__init__({
            'id': Event.generate_id(),
            'time': time.time(),
            'name': name,
            'payload': payload
        })

    @staticmethod
    def generate_id():
        Event.__lock.acquire()
        Event.__id += 1
        event_id = Event.__id
        Event.__lock.release()
        return event_id

    @property
    def id(self) -> int:
        return self.get('id')

    @property
    def time(self) -> float:
        return self.get('time')

    @property
    def name(self) -> str:
        return self.get('name')

    @property
    def payload(self) -> dict:
        return self.get('payload')

    @staticmethod
    def from_dict(data: dict):
        return Event(data.get('name'), data.get('payload'))


class EventDispatch:
    REGISTRATION_EVENT = 'event_center.handler_registered'
    UNREGISTRATION_EVENT = 'event_center.handler_unregistered'

    __ALL_EVENTS = '*'
    __EVENT_LOG_SIZE = 5

    __instance = None
    __logger = logging.getLogger(__name__)
    __lock = threading.Lock()

    __event_handlers = {}

    # --- For testing purposes ------------------------------------------------------------------------------
    __event_log = deque(maxlen=__EVENT_LOG_SIZE)
    __log_event = False
    __log_event_if_no_handlers = False

    def toggle_event_logging(self, is_log: bool = False):
        self.__log_event = is_log

    @property
    def event_log(self) -> deque:
        return self.__event_log

    def clear_event_log(self):
        self.__event_log = deque(maxlen=self.__EVENT_LOG_SIZE)

    @property
    def log_event_if_no_handlers(self):
        return self.__log_event_if_no_handlers

    @log_event_if_no_handlers.setter
    def log_event_if_no_handlers(self, value):
        self.__log_event_if_no_handlers = value

    @property
    def event_handlers(self) -> dict:
        return self.__event_handlers

    @property
    def all_event_handlers(self) -> [Callable]:
        return self.__event_handlers.get(self.__ALL_EVENTS, [])

    def clear_registered_handlers(self):
        self.__event_handlers = {}

    # -------------------------------------------------------------------------------------------------------

    def __new__(cls):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def register(self, handler: Callable, events: [str]):
        self.__validate_events(events)

        if not events:
            # Registering for all events.
            events = [self.__ALL_EVENTS]

        is_registered_for_event = False
        for event in events:
            if self.__register_for_event(handler, event):
                is_registered_for_event = True

        if is_registered_for_event:
            self.__post_admin_event__registered(handler, events)
            self.__log_message_registered(handler, events)

    def unregister(self, handler: Callable, events: [str]):
        self.__validate_events(events)

        self.__lock.acquire()

        if not events:
            # Unregistering from all events.
            events = [self.__ALL_EVENTS]

        is_unregistered_for_event = False
        for event in events:
            if self.__unregister_from_event(handler, event):
                is_unregistered_for_event = True

        self.__lock.release()

        if is_unregistered_for_event:
            self.__post_admin_event__unregistered(handler, events)
            self.__log_message_unregistered(handler, events)

    def post_event(self, name: str, payload: dict = None):
        self.__lock.acquire()

        payload = payload if payload else {}
        event = Event(name, payload)

        # Get handlers for event.
        event_handlers = self.__event_handlers.get(name, [])

        # Get all-event handlers.
        all_event_handlers = self.__event_handlers.get(self.__ALL_EVENTS, [])

        # Combine handlers and all-event handlers into one unique list (in case some handlers are registered for both).
        for handler in all_event_handlers:
            if handler not in event_handlers:
                event_handlers.append(handler)

        # Log event posting info.
        if self.__log_event and (event_handlers or self.__log_event_if_no_handlers):
            self.__event_log.append(event)

        # Skip notifying if there's no handler registered for event.
        if not event_handlers:
            self.__log_message_not_propagating_event(name)
            self.__lock.release()
            return

        # Notify all handlers using threads (so handlers don't need to implement their own thread).
        for handler in event_handlers:
            t = threading.Thread(target=handler, args=[event])
            t.start()

        self.__log_message_posted_event(event)

        self.__lock.release()

    def __register_for_event(self, handler: Callable, event: str) -> bool:
        try:
            handlers = self.__event_handlers[event]
            # Skip adding handler if already registered for event.
            if handler not in handlers:
                handlers.append(handler)
                return True
        except KeyError:
            # First handler for event.
            self.__event_handlers[event] = [handler]
            return True
        return False

    def __unregister_from_event(self, handler: Callable, event: str) -> bool:
        try:
            handlers = self.__event_handlers.get(event, [])
            if handler not in handlers:
                # Nothing to do...handler is not registered for event.
                return False
            handlers.remove(handler)
        except KeyError:
            # Nothing to do...handler is not registered for event.
            return False
        return True

    @staticmethod
    def __validate_events(events: [str]):
        invalid_events = []
        for event in events:
            if not event or event == EventDispatch.__ALL_EVENTS:
                invalid_events.append(event)
        if len(invalid_events) > 0:
            raise InvalidEventError

    def __post_admin_event__registered(self, handler: Callable, events: [str]):
        # Replace internal marking for 'all events' with an empty list.
        if events == [self.__ALL_EVENTS]:
            events = []
        self.post_event(self.REGISTRATION_EVENT, {
            'events': events,
            'handler': repr(handler)
        })

    def __post_admin_event__unregistered(self, handler: Callable, events: [str]):
        # Replace internal marking for 'all events' with an empty list.
        if events == [self.__ALL_EVENTS]:
            events = []
        self.post_event(self.UNREGISTRATION_EVENT, {
            'events': events,
            'handler': repr(handler)
        })

    def __log_message_registered(self, handler: Callable, events: [str]):
        message = f"Registered '{handler}'for event(s): {events}"
        self.__logger.debug(message)

    def __log_message_unregistered(self, handler: Callable, events: [str]):
        message = f"Unregistered '{handler}' from event(s): {events}"
        self.__logger.debug(message)

    def __log_message_not_propagating_event(self, event: str):
        message = f"Not propagating '{event}'...no handlers for it"
        self.__logger.debug(message)

    def __log_message_posted_event(self, event: Event):
        message = f"Posted event'{event.name}'"
        self.__logger.debug(message)


class InvalidEventError(NotifiableError):
    def __init__(self, events: [str]):
        message = ''
        error = 'invalid_events'
        payload = {
            'events': events
        }
        super().__init__(message, error, payload)
