from typing import Callable, Any, Dict

import pytest

from eventdispatch.core import Event, EventDispatch, EventDispatchEvent, EventDispatchManager


class EventHandler:
    def __init__(self):
        self.received_events = {}

    def on_event(self, event: Event):
        if event.name in self.received_events:
            message = f'Same event received again'
            message += f'\nEvent1: {self.received_events[event.name].dict}'
            message += f'\nEvent2: {event.dict}'
            pytest.fail(message)

        self.received_events[event.name] = event


def register_handler_for_event(handler, event: str = None):
    event_log_count = len(EventDispatchManager().default_dispatch.event_log)
    handler_count = get_handler_count()

    events = [event] if event else []

    register(handler, events)
    validate_expected_handler_count(handler_count + 1)
    validate_event_log_count(event_log_count + 1)


def register(handler: EventHandler, events: [str]):
    EventDispatchManager().default_dispatch.register(handler.on_event, events)


def get_handler_count():
    count = 0

    for event_name, handlers in EventDispatchManager().default_dispatch.event_handlers.items():
        count += len(handlers)
    return count


def get_event_log_count() -> int:
    return len(EventDispatchManager().default_dispatch.event_log)


def validate_event_log_count(expected_count: int):
    assert get_event_log_count() == expected_count


def validate_expected_handler_count(expected_count: int):
    assert get_handler_count() == expected_count


def validate_handler_registered_for_all_events(handler: EventHandler):
    validate_test_handler_registered_for_event(handler, None)


def validate_test_handler_registered_for_event(handler: EventHandler, event: str = None):
    validate_handler_registered_for_event(handler.on_event, event)


def validate_test_handler_not_registered_for_event(handler: EventHandler, event: str = None):
    validate_handler_not_registered_for_event(handler.on_event, event)


def validate_handler_registered_for_event(handler: Callable, event: str = None):
    assert handler in get_registered_handlers_for_event(event)


def validate_handler_not_registered_for_event(handler: Callable, event: str = None):
    assert handler not in get_registered_handlers_for_event(event)


def get_registered_handlers_for_event(event: str = None) -> [Callable]:
    # Check if validating for all events.
    if not event:
        return EventDispatchManager().default_dispatch.all_event_handlers
    else:
        return EventDispatchManager().default_dispatch.event_handlers.get(event, [])


def validate_received_events(handler: EventHandler, expected_events: [Any], is_ignore_registration_event: bool = True):
    expected_events = EventDispatch.to_string_events(expected_events)
    registration_event = EventDispatch.to_string_event(EventDispatchEvent.HANDLER_REGISTERED)
    if is_ignore_registration_event:
        if registration_event in handler.received_events:
            handler.received_events.pop(registration_event)

    assert len(handler.received_events) == len(expected_events)

    validated_events = []
    for expected_event in expected_events:
        assert expected_event in handler.received_events
        validated_events.append(expected_event)

    # Remove received events that have been validated.
    for event in validated_events:
        handler.received_events.pop(event)


def validate_received_event(handler: EventHandler, expected_event: Any, expected_payload: Dict[str, Any]):
    expected_event = EventDispatch.to_string_event(expected_event)
    for name, event in handler.received_events.items():
        if name == expected_event:
            if not expected_payload:
                return

            if event.payload.keys() == expected_payload.keys():
                # if event.payload == expected_payload:
                return
    pytest.fail(f'Could not find expected event: {expected_event}')


def validate_event_not_received(handler: EventHandler, expected_event: Any):
    expected_event = EventDispatch.to_string_event(expected_event)
    assert expected_event not in handler.received_events
