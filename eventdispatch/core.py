import datetime
import hashlib
import json
import logging
import threading
import time
import traceback
from collections import deque
from enum import Enum
from queue import Queue
from typing import Callable, Dict, Any, Union, List

from wrapt import synchronized

from eventdispatch.decorators import singleton


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
    def json(self, pretty_print: bool = False) -> str:
        return json.dumps(self.__data, indent=4) if pretty_print else json.dumps(self.__data)


class Event(Data):
    __id = 0

    def __init__(self, name: [Union[str, Enum, NamespacedEnum]], payload: Dict[str, Any] = None):
        if not name:
            raise InvalidEventError([name])

        super(Event, self).__init__({
            'id': Event.generate_id(),
            'time': time.time(),
            'name': EventDispatch.to_string_event(name),
            'payload': payload if payload else {}
        })

    @staticmethod
    @synchronized
    def generate_id():
        Event.__id += 1
        return Event.__id

    @property
    def id(self) -> int:
        return self.get('id')

    @property
    def time(self) -> float:
        return self.get('time')

    @property
    def time_formatted(self) -> str:
        t = datetime.datetime.fromtimestamp(self.get('time'))
        return t.strftime('%Y-%m-%d %H:%M:%S')

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


def map_events(events_to_map: [Event], event_to_post: Event, ignore_if_exists: bool = False) -> str:
    """
    Maps an event to be posted when all specified events occur.
    :param events_to_map: list of Event objects (event name and payload) to be watched
    :param event_to_post: Event object (event name and payload) to be posted when all watched events occur
    :param ignore_if_exists: Skip attempt to map events if a map for given events already exists.
    :return: unique key for this event map (currently built using only events_to_map)
    """
    return EventDispatchManager().default_dispatch.map_events(events_to_map, event_to_post, ignore_if_exists)


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

        self.message = message
        self.error = error
        self.payload = payload
        self.exception = exception

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


class EventMapper:
    def map_events(self, events_to_map: [Event], event_to_post: Event, reset_if_exists: bool = False):
        pass

    @property
    def event_maps(self) -> Dict[str, Any]:
        return {}

    def unregister_from_events(self):
        pass

    def on_event(self, event: Event):
        pass


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
    def event_handlers(self) -> Dict[str, List[Callable]]:
        return self.__event_handlers

    @property
    def all_event_handlers(self) -> [Callable]:
        return self.__event_handlers.get(self.__ALL_EVENTS, [])

    def clear_registered_handlers(self):
        self.__event_handlers: Dict[str, List[Callable]] = {}

    @property
    def serialized_event_handlers(self) -> Dict[str, Any]:
        serialized_handlers = {}
        for event, handlers in self.__event_handlers.items():
            str_handlers = []
            for handler in handlers:
                str_handlers.append(self.prune_handler(str(handler)))
            serialized_handlers[event] = str_handlers
        return serialized_handlers

    @staticmethod
    def prune_handler(handler_string: str) -> str:
        if handler_string.startswith('<function'):
            x = handler_string.split(' at ')[0]
            x = x.split('<function ')
            return x[1]

        if handler_string.startswith('<bound method'):
            x = handler_string.split(' of ')[0]
            x = x.split('<bound method ')
            return x[1]
        return handler_string

    # -------------------------------------------------------------------------------------------------------

    def __init__(self, channel: str = '', pretty_print: bool = False):
        self.__channel = channel
        self.__event_handlers: Dict[str, List[Callable]] = {}
        self.__event_queue: Queue = Queue()
        self.__event_mapper = None

        self.pretty_print = pretty_print

        # --- For testing purposes ------------------------------------------------------------------------------
        self.__event_log = deque(maxlen=self.__EVENT_LOG_SIZE)
        self.__log_event: bool = False
        self.__log_event_if_no_handlers: bool = False
        # -------------------------------------------------------------------------------------------------------

        threading.Thread(target=self.monitor_event_queue, daemon=True).start()

    def register(self, handler: Callable, events: [str]):
        self.__validate_events(events)

        is_registered_for_event = False

        with synchronized(self):
            if not events:
                # Registering for all events.
                events = [self.__ALL_EVENTS]

            for event in events:
                if self.__register_for_event(handler, event):
                    is_registered_for_event = True

        if is_registered_for_event:
            self.__post_admin_event_registration(handler, events, is_registered=True)
            self.__log_message_registered(handler, events)

    def unregister(self, handler: Callable, events: [str]):
        self.__validate_events(events)

        is_unregistered_for_event = False

        with synchronized(self):
            if not events:
                # Unregistering from all events.
                events = [self.__ALL_EVENTS]

            for event in events:
                if self.__unregister_from_event(handler, event):
                    is_unregistered_for_event = True

        if is_unregistered_for_event:
            self.__post_admin_event_registration(handler, events, is_registered=False)
            self.__log_message_unregistered(handler, events)

    def post_event(self, name: str, payload: Dict[str, Any] = None, exclude_handler: Callable[[Event], None] = None):
        with synchronized(self):
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
                return

            # Notify all handlers using threads (so handlers don't need to implement their own thread).
            for handler in event_handlers:
                # Add thread to notify handler onto event queue (so event order would be maintained per handler).
                self.__event_queue.put(threading.Thread(target=handler, args=[event]))

            self.__log_message_posted_event(event)

    def monitor_event_queue(self):
        while True:
            thread = self.__event_queue.get()
            thread.start()
            self.__event_queue.task_done()

    def set_event_map_manager(self, event_mapper: EventMapper):
        if self.__event_mapper:
            # Unregister current mapper from receiving events (if any) for which it had registered.
            self.__event_mapper.unregister_from_events()

        # Set new event mapper.
        self.__event_mapper = event_mapper

    def map_events(self, events_to_map: [Event], event_to_post: Event, ignore_if_exists: bool = False) -> str:
        if not self.__event_mapper:
            self.__event_mapper = EventMapManager(self)
        return self.__event_mapper.map_events(events_to_map, event_to_post, ignore_if_exists)

    def get_event_maps(self):
        return self.__event_mapper.event_maps

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


@singleton
class EventDispatchManager:
    __pretty_print: bool

    def __init__(self, pretty_print: bool = False):
        self.__pretty_print = pretty_print

        # Create default event dispatcher (for local events, as well as events without a channel).
        self.__event_dispatchers: Dict[str, EventDispatch] = {
            '': EventDispatch(pretty_print=pretty_print)
        }

    @property
    def event_dispatchers(self) -> Dict[str, EventDispatch]:
        return self.__event_dispatchers

    @property
    def default_dispatch(self) -> EventDispatch:
        return self.__event_dispatchers['']

    def add_event_dispatch(self, channel: str) -> bool:
        if channel not in self.__event_dispatchers:
            self.__event_dispatchers[channel] = EventDispatch(channel, self.__pretty_print)
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


class EventMapEvent(NamespacedEnum):
    MAPPING_CREATED = 'mapping_created'
    MAPPING_RESET = 'mapping_reset'
    MAPPING_TRIGGERED = 'mapping_triggered'
    MAPPING_REMOVED = 'mapping_removed'

    def get_namespace(self) -> str:
        return 'event_map'


class DuplicateMappingError(NotifiableError):
    def __init__(self, events_to_map: [Event], event_to_post: Event):
        message = f"Mapping for events provided already exists."
        error = 'duplicate_mapping'
        payload = EventMapUtil.build_event_mapping_payload(events_to_map, event_to_post)
        super().__init__(message, error, payload)


class InvalidMappingEventsError(NotifiableError):
    def __init__(self, events_to_map: [Event], event_to_post: Event):
        message = f"Invalid events provided for event mapping."
        error = 'invalid_events'
        payload = EventMapUtil.build_event_mapping_payload(events_to_map, event_to_post)
        super().__init__(message, error, payload)


class MappingNotFoundError(NotifiableError):
    def __init__(self, key: str):
        message = f"Mapping not found for key: {key}"
        error = 'mapping_not_found'
        payload = {
            'key': key
        }
        super().__init__(message, error, payload)


class EventMap:
    def __init__(self, event_dispatch: EventDispatch, events_to_map: [Event], event_to_post: Event, key: str):
        if not events_to_map or not event_to_post or not any(events_to_map):
            raise InvalidMappingEventsError(events_to_map, event_to_post)
        self.__event_dispatch = event_dispatch
        self.__events_to_map = events_to_map
        self.__event_to_post = event_to_post
        self.__events_to_watch = {event.name: event.payload for event in self.__events_to_map}
        self.__mapped_events = [event.name for event in events_to_map]

        self.__key = key

        self.__event_dispatch.register(self.on_event, self.__mapped_events)

    @property
    def events_to_watch(self) -> [str]:
        return self.__events_to_watch

    @property
    def events_to_map(self) -> [Event]:
        return self.__events_to_map

    @property
    def event_to_post(self) -> Event:
        return self.__event_to_post

    @synchronized
    def on_event(self, event: Event):
        try:
            # Check if event is being watched.
            payload_to_watch = self.__events_to_watch[event.name]

            # Check event payload for matching keys and values from payload being watched.
            for expected_key, expected_value in payload_to_watch.items():
                try:
                    value = event.payload.get(expected_key)
                    if value != expected_value:
                        return
                except KeyError:
                    # Event does not have expected payload to watch.
                    return
        except KeyError:
            # Not event/payload that is being watched, or event already occurred (and was removed from watch list).
            return

        # Expected keys are present, and expected values confirmed.  Event is expected.
        del self.__events_to_watch[event.name]

        # Post mapped event if all expected events have been received.
        if not self.__events_to_watch:
            self.__event_dispatch.post_event(self.__event_to_post.name, self.__event_to_post.payload)
            self.stop()

    def stop(self):
        self.__event_dispatch.unregister(self.on_event, self.__mapped_events)
        self.__event_dispatch.post_event(EventMapEvent.MAPPING_TRIGGERED.namespaced_value, {'key': self.__key})


class EventMapManager(EventMapper):
    __logger = logging.getLogger(__name__)

    def __init__(self, event_dispatch: EventDispatch):
        self.__event_maps = {}
        self.__event_dispatch = event_dispatch
        event_dispatch.register(self.on_event, [EventMapEvent.MAPPING_TRIGGERED.namespaced_value])

    @property
    def event_maps(self) -> Dict[str, Any]:
        return self.__event_maps

    def map_events(self, events_to_map: [Event], event_to_post: Event, ignore_if_exists: bool = False) -> str:
        if not events_to_map or not event_to_post:
            raise InvalidMappingEventsError(events_to_map, event_to_post)

        key = self.build_key(events_to_map)
        if key in self.__event_maps:
            if ignore_if_exists:
                self.__log_message_ignoring_duplicate_event_mapping(events_to_map, event_to_post)
                return key
            else:
                self.__log_message_duplicate_event_mapping(events_to_map, event_to_post)
                raise DuplicateMappingError(events_to_map, event_to_post)

        # Create and store event map.
        self.__event_maps[key] = EventMap(self.__event_dispatch, events_to_map, event_to_post, key)
        event_name = EventMapEvent.MAPPING_CREATED
        payload = EventMapUtil.build_event_mapping_payload(events_to_map, event_to_post)
        self.__event_dispatch.post_event(event_name.namespaced_value, payload)

        return key

    def remove_event_map_by_key(self, key: str):
        try:
            event_map = self.__event_maps.pop(key)
            payload = EventMapUtil.build_event_mapping_payload(event_map.events_to_map, event_map.event_to_post)
            self.__event_dispatch.post_event(EventMapEvent.MAPPING_REMOVED.namespaced_value, payload)
        except KeyError:
            raise MappingNotFoundError(key)

    def on_event(self, event: Event):
        if event.name != EventMapEvent.MAPPING_TRIGGERED.namespaced_value:
            return

        key = event.payload.get('key')
        try:
            self.remove_event_map_by_key(key)
        except MappingNotFoundError:
            pass

    def unregister_from_events(self):
        self.__event_dispatch.unregister(self.on_event, [EventMapEvent.MAPPING_TRIGGERED])

    def __log_message_ignoring_duplicate_event_mapping(self, events_to_map: [Event], event_to_post: Event):
        payload = EventMapUtil.build_event_mapping_payload(events_to_map, event_to_post)
        if self.__event_dispatch.pretty_print:
            payload = json.dumps(payload, indent=2) + '\n'
        else:
            payload = f"{payload}'\n'"

        message = f"Ignoring event mapping request...mapping already exists\n{payload}"
        EventMapManager.__logger.debug(message)

    def __log_message_duplicate_event_mapping(self, events_to_map: [Event], event_to_post: Event):
        payload = EventMapUtil.build_event_mapping_payload(events_to_map, event_to_post)
        if self.__event_dispatch.pretty_print:
            payload = json.dumps(payload, indent=2) + '\n'
        else:
            payload = f"{payload}'\n'"
        message = f"Duplicate event mapping\n{payload}"
        EventMapManager.__logger.error(message)

    @staticmethod
    def build_key(events_to_map: [Event]) -> str:

        # Convert list of Event objects to list of event dictionaries.
        event_dicts = [event.dict for event in events_to_map]

        # Sort event dictionaries by event name.
        sorted_events = sorted(event_dicts, key=lambda x: x['name'])

        # Create string of sorted event names.
        events = ','.join([event['name'] for event in sorted_events])

        # Create string of ordered and sorted event payloads.
        payload = ','.join([json.dumps(event['payload'], sort_keys=True) for event in sorted_events])

        # Encode event name and event payload strings into a unique string.
        return EventMapUtil.encode_string(f'{events}{payload}')


class EventMapUtil:
    @staticmethod
    def build_event_mapping_payload(events_to_map: [Event], event_to_post: Event) -> Dict[str, Any]:
        if not (events_to_map is None or events_to_map == [] or any(element is None for element in events_to_map)):
            events_to_map = [event.dict for event in events_to_map]
            events_to_map = [EventMapUtil.remove_unique_items_from_event(event) for event in events_to_map]

        if event_to_post:
            event_to_post = event_to_post.dict
            event_to_post = EventMapUtil.remove_unique_items_from_event(event_to_post)

        return {
            'events_to_map': events_to_map,
            'event_to_post': event_to_post
        }

    @staticmethod
    def remove_unique_items_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in event.items() if key not in ['id', 'time']}

    @staticmethod
    def encode_string(value: str) -> str:
        h = hashlib.sha256()
        h.update(value.encode('utf-8'))
        return h.hexdigest()
