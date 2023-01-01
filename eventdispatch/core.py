import json
import logging
import threading
import time
import traceback
from collections import deque
from enum import Enum
from queue import Queue
from typing import Callable, Dict, Any, Union


class NamespacedEnum(Enum):
    """
    Adds a namespace (optional) to prepend to enum values.  To set namespace, override the "get_namespace(self)"
    to return desired namespace.
    """

    def __init__(self, _):
        self.__namespace = self.get_namespace()

    def get_namespace(self) -> str:
        pass

    @property
    def namespaced_value(self) -> str:
        return f'{self.__namespace}.{self.value}' if self.__namespace else self.value


class Data:
    def __init__(self, data: Dict[str, Any]):
        if data is None:
            raise InvalidDataError()
        self.__data = data

    def get(self, key: str, data: Dict[str, Any] = None):
        data = data if data else self.__data
        try:
            return data[key]
        except KeyError:
            raise MissingKeyError(key, data)

    @property
    def dict(self) -> Dict[str, Any]:
        return self.__data

    @property
    def json(self) -> str:
        return json.dumps(self.__data)


class Event(Data):
    __lock = threading.Lock()
    __id = 0

    def __init__(self, name: str, payload: Dict[str, Any] = None):
        super(Event, self).__init__({
            'id': Event.generate_id(),
            'time': time.time(),
            'name': name,
            'payload': payload if payload else {}
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
    def payload(self) -> Dict[str, Any]:
        return self.get('payload')

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return Event(data.get('name'), data.get('payload'))


def register_for_events(handler: Callable[[Event], None], events: [Union[str, Enum, NamespacedEnum]]):
    """
    Registers for the specified events
    :param handler: callback function that will be called when specified event occurs
    :param events: list of event names/types (string or Enum or NamespacedEnum) for which to register
    :return:
    """
    if not handler:
        return
    EventDispatchManager().default_dispatch.register(handler, EventDispatch.to_string_events(events))


def unregister_from_events(handler: Callable[[Event], None], events: [Union[str, Enum, NamespacedEnum]]):
    """
    Unregisters from the specified events
    :param handler: callback function that was provided when registering
    :param events: list of event names/types (string or Enum or NamespacedEnum) from which to unregister
    :return: None
    """
    if not handler:
        return
    EventDispatchManager().default_dispatch.unregister(handler, EventDispatch.to_string_events(events))


def post_event(event: [Union[str, Enum, NamespacedEnum]], payload: Dict[str, Any] = None,
               exclude_handler: Callable[[Event], None] = None):
    """
    Posts an event (with optional payload of info) for which registered listeners (callbacks) can get notified.
    :param event: event name/type (string or Enum or NamespacedEnum) to post
    :param payload: optional dictionary of keyed-values to include with the event
    :param exclude_handler: optional handler to exclude from getting the event posted
    :return: None
    """

    if not event:
        return
    EventDispatchManager().default_dispatch.post_event(EventDispatch.to_string_event(event), payload, exclude_handler)


class NotifiableError(Exception):
    """Base error that posts event for this error"""

    def __init__(self, message: str, error: str, payload: Dict[str, Any], exception: traceback = None):
        # Check if subclass provided an error already, which could be a sub-error type.
        if 'error' not in payload:
            payload['error'] = error

        if exception:
            payload['stacktrace'] = ''.join(
                traceback.format_exception(etype=type(exception), value=exception, tb=exception.__traceback__))

        if message:
            payload['message'] = message

        super().__init__(message)
        post_event(error, payload)


class InvalidDataError(NotifiableError):
    def __init__(self):
        message = "Cannot create data object from 'None' data input"
        error = 'invalid_data_input'
        payload = {}
        super().__init__(message, error, payload)


class MissingKeyError(NotifiableError):
    def __init__(self, key: str, data: Dict[str, Any]):
        message = f"Could not find key '{key}' within data:\n{data}."
        error = 'missing_key'
        payload = {
            'key': key,
            'data': data
        }
        super().__init__(message, error, payload)


class EventDispatchEvent(NamespacedEnum):
    HANDLER_REGISTERED = 'handler_registered'
    HANDLER_UNREGISTERED = 'handler_unregistered'

    def get_namespace(self) -> str:
        return 'event_dispatch'


class EventDispatch:
    __ALL_EVENTS = '*'
    __EVENT_LOG_SIZE = 5

    __logger = logging.getLogger(__name__)

    # --- For testing purposes ------------------------------------------------------------------------------
    def toggle_event_logging(self, is_log: bool = False):
        self.__log_event = is_log

    @property
    def event_log(self) -> deque:
        return self.__event_log

    def clear_event_log(self):
        self.__event_log = deque(maxlen=self.__EVENT_LOG_SIZE)

    @property
    def log_event_if_no_handlers(self) -> bool:
        return self.__log_event_if_no_handlers

    @log_event_if_no_handlers.setter
    def log_event_if_no_handlers(self, value):
        self.__log_event_if_no_handlers = value

    @property
    def event_handlers(self) -> Dict[str, list[Callable]]:
        return self.__event_handlers

    @property
    def all_event_handlers(self) -> [Callable]:
        return self.__event_handlers.get(self.__ALL_EVENTS, [])

    def clear_registered_handlers(self):
        self.__event_handlers: Dict[str, list[Callable]] = {}

    # -------------------------------------------------------------------------------------------------------

    def __init__(self, channel: str = ''):
        self.__channel = channel
        self.__lock = threading.Lock()
        self.__event_handlers: Dict[str, list[Callable]] = {}
        self.__event_queue: Queue = Queue()

        # --- For testing purposes ------------------------------------------------------------------------------
        self.__event_log = deque(maxlen=self.__EVENT_LOG_SIZE)
        self.__log_event: bool = False
        self.__log_event_if_no_handlers: bool = False
        # -------------------------------------------------------------------------------------------------------

        threading.Thread(target=self.monitor_event_queue, daemon=True).start()

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
            self.__post_admin_event_registration(handler, events, is_registered=True)
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
            self.__post_admin_event_registration(handler, events, is_registered=False)
            self.__log_message_unregistered(handler, events)

    def post_event(self, name: str, payload: Dict[str, Any] = None, exclude_handler: Callable[[Event], None] = None):
        self.__lock.acquire()

        payload = payload if payload else {}
        event = Event(name, payload)

        # Get handlers for event.
        event_handlers = self.__event_handlers.get(name, [])

        # Get all-event handlers.
        all_event_handlers = self.__event_handlers.get(self.__ALL_EVENTS, [])

        # Combine handlers and all-event handlers into one unique list (in case some handlers are registered for both).
        for handler in all_event_handlers:
            if handler not in event_handlers and handler != exclude_handler:
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
            # Add thread to notify handler onto event queue (so event order would be maintained per handler).
            self.__event_queue.put(threading.Thread(target=handler, args=[event]))

        self.__log_message_posted_event(event)

        self.__lock.release()

    def monitor_event_queue(self):
        while True:
            thread = self.__event_queue.get()
            thread.start()
            self.__event_queue.task_done()

    @staticmethod
    def to_string_events(events: [Any]) -> [str]:
        string_events = []
        for event in events:
            string_events.append(EventDispatch.to_string_event(event))
        return string_events

    @staticmethod
    def to_string_event(event: [Any]) -> str:
        if isinstance(event, NamespacedEnum):
            return str(event.namespaced_value)
        elif isinstance(event, Enum):
            return str(event.value)
        else:
            return event

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

    def __post_admin_event_registration(self, handler: Callable, events: [str], is_registered: bool):
        name = EventDispatchEvent.HANDLER_REGISTERED.namespaced_value if is_registered else \
            EventDispatchEvent.HANDLER_UNREGISTERED.namespaced_value

        # Replace internal marking for 'all events' with an empty list.
        if events == [self.__ALL_EVENTS]:
            events = []
        self.post_event(name, {
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
        message = f"Posted event '{event.name}'"
        self.__logger.debug(message)


class EventDispatchManager:
    __instance = None
    __event_dispatchers: Dict[str, EventDispatch] = {}

    def __new__(cls):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)

            # Create default event dispatcher (for local events, as well as events without a channel).
            cls.__event_dispatchers[''] = EventDispatch()
        return cls.__instance

    @property
    def event_dispatchers(self) -> Dict[str, EventDispatch]:
        return self.__event_dispatchers

    @property
    def default_dispatch(self) -> EventDispatch:
        return self.__event_dispatchers['']

    def add_event_dispatch(self, channel: str) -> bool:
        if channel not in self.__event_dispatchers:
            self.__event_dispatchers[channel] = EventDispatch(channel)
            return True
        return False

    def remove_event_dispatch(self, channel: str):
        if channel in self.__event_dispatchers:
            del self.__event_dispatchers[channel]
            return True
        return False


class InvalidEventError(NotifiableError):
    def __init__(self, events: [str]):
        message = ''
        error = 'invalid_events'
        payload = {
            'events': events
        }
        super().__init__(message, error, payload)
