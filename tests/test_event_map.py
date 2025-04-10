import time
from typing import Dict, Any

import pytest

from eventdispatch import Event
from eventdispatch.core import EventMap, EventDispatch, EventDispatchManager, post_event, InvalidMappingEventsError, \
    EventMapEvent
from helper import EventHandler, register, get_event_log_count, validate_event_log_count, \
    validate_handler_not_registered_for_event, validate_event_not_received, validate_handler_registered_for_event, \
    validate_received_event

event_dispatch: EventDispatch
handler1: EventHandler

event_to_watch_1 = 'event_1'
event_to_watch_2 = 'event_2'
event_to_map = 'event_3'


def setup_module():
    global event_dispatch
    event_dispatch = EventDispatchManager().default_dispatch
    event_dispatch.toggle_event_logging(True)


def setup_function():
    global handler1, event_dispatch

    event_dispatch.clear_event_log()
    event_dispatch.clear_registered_handlers()
    event_dispatch.log_event_if_no_handlers = True

    handler1 = EventHandler()


def teardown_function():
    pass


def teardown_module():
    global event_dispatch
    event_dispatch.toggle_event_logging(False)


@pytest.mark.parametrize('events_to_watch', [None, '', [], [None, None]])
def test_constructor__when_no_events_to_watch(events_to_watch: [Event]):
    # Objective:
    # Exception is thrown.

    global event_dispatch

    # Setup
    event_to_post = Event(event_to_map, {})

    # Test
    try:
        EventMap(event_dispatch, events_to_watch, event_to_post, '')
        pytest.fail('Expected to get exception')
    except InvalidMappingEventsError:
        pass

    # Verify
    # (none)


@pytest.mark.parametrize('event_to_post', [None])
def test_constructor__when_no_mapped_event(event_to_post: Event):
    # Objective:
    # Exception is thrown.

    global event_dispatch

    # Setup
    events_to_map = [
        Event(event_to_watch_1, {}),
        Event(event_to_watch_2, {}),
    ]

    # Test
    try:
        EventMap(event_dispatch, events_to_map, event_to_post, '')
        pytest.fail('Expected to get exception')
    except InvalidMappingEventsError:
        pass

    # Verify
    # (none)


def test_constructor():
    # Objective:
    # Event map is watching for expected events.
    # Event map is registered for each event to watch.

    global event_dispatch

    # Setup
    events_to_map = [
        Event(event_to_watch_1, {}),
        Event(event_to_watch_2, {}),
    ]
    event_to_post = Event(event_to_map, {})

    # Test
    event_map = EventMap(event_dispatch, events_to_map, event_to_post, '')

    # Verify
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])
    validate_handler_registered_for_event(event_map.on_event, event_to_watch_1)
    validate_handler_registered_for_event(event_map.on_event, event_to_watch_2)


def test_on_event__when_not_last_event__no_payload():
    # Objective:
    # Events being watched are updated (1 less event being watched).
    # Events map does not generated mapped event.

    # Setup
    event_map = create_event_map_with_no_payload([event_to_watch_1, event_to_watch_2], event_to_map)
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])
    expected_event_count = get_event_log_count()

    # Test
    post_event(event_to_watch_1, {})

    # Verify
    time.sleep(0.2)
    expected_event_count += 1
    verify_events_to_watch(event_map, [event_to_watch_2])
    validate_event_log_count(expected_event_count)


@pytest.mark.parametrize('payload', [
    {'id': 10},
    {'age': 20},
    {'name': 'Jack'},
])
def test_on_event__when_not_last_event__payload_does_not_match(payload: Dict[str, Any]):
    # Objective:
    # Events to watch are still the same.

    global event_dispatch

    # Setup
    event_1_to_watch = Event(event_to_watch_1, {'id': 5})
    event_2_to_watch = Event(event_to_watch_2, {})
    event_to_post = Event(event_to_map, {})
    event_map = EventMap(event_dispatch, [event_1_to_watch, event_2_to_watch], event_to_post, '')
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])

    # Test
    post_event(event_to_watch_1, payload)

    # Verify
    time.sleep(0.2)
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])


@pytest.mark.parametrize('payload', [
    {'id': 5},
    {'id': 5, 'name': 'Jane'}
])
def test_on_event__when_not_last_event__payload_matches(payload: Dict[str, Any]):
    # Objective:
    # Events being watched are updated (1 less event being watched).
    # Events map does not generated mapped event.

    global event_dispatch

    # Setup
    expected_payload = payload
    event_1_to_watch = Event(event_to_watch_1, expected_payload)
    event_2_to_watch = Event(event_to_watch_2, {})
    event_to_post = Event(event_to_map, {})
    event_map = EventMap(event_dispatch, [event_1_to_watch, event_2_to_watch], event_to_post, '')
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])

    # Test
    post_event(event_to_watch_1, expected_payload)

    # Verify
    time.sleep(0.2)
    verify_events_to_watch(event_map, [event_to_watch_2])


@pytest.mark.parametrize('payload', [
    {'id': 5, 'age': 30},
    {'id': 5, 'name': 'Jane'}
])
def test_on_event__when_not_last_event__some_payload_matches(payload: Dict[str, Any]):
    # Objective:
    # Events to watch are still the same.

    global event_dispatch

    # Setup
    expected_payload = {'id': 5, 'name': 'Jim'}
    event_1_to_watch = Event(event_to_watch_1, expected_payload)
    event_2_to_watch = Event(event_to_watch_2, {})
    event_to_post = Event(event_to_map, {})
    event_map = EventMap(event_dispatch, [event_1_to_watch, event_2_to_watch], event_to_post, '')
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])

    # Test
    post_event(event_to_watch_1, payload)
    # Verify
    time.sleep(0.2)
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])


def test_on_event__when_repeat_event__no_payload():
    # Objective:
    # Events being watched are not updated.
    # Events map does not generated mapped event.

    # Setup
    event_map = create_event_map_with_no_payload([event_to_watch_1, event_to_watch_2], event_to_map)
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])
    expected_event_count = get_event_log_count()

    post_event(event_to_watch_1, {})
    expected_event_count += 1

    time.sleep(0.2)
    verify_events_to_watch(event_map, [event_to_watch_2])

    # Test
    post_event(event_to_watch_1, {})

    # Verify
    time.sleep(0.2)
    expected_event_count += 1
    verify_events_to_watch(event_map, [event_to_watch_2])
    validate_event_log_count(expected_event_count)


@pytest.mark.parametrize('mapping_payload,post_payload', [
    ({}, {}),
    ({'id': 5}, {}),
    ({'id': 5, 'age': 30}, {}),
    ({'id': 5, 'name': 'Jane'}, {}),
    ({'id': 5}, {'key': 'value'}),
])
def test_on_event__when_last_event(mapping_payload: Dict[str, Any], post_payload: Dict[str, Any]):
    # Objective:
    # Events being watched are updated (no more events being watched).
    # Payload keys/values are used to determine a match.
    # Events map generates mapped event, and mapping-triggered event.
    # Event map unregistered from events being watched.

    global event_dispatch, handler1

    # Setup
    register(handler1, [event_to_map, EventMapEvent.MAPPING_TRIGGERED.namespaced_value])

    event_1_to_watch = Event(event_to_watch_1, {})
    event_2_to_watch = Event(event_to_watch_2, mapping_payload)
    event_to_post = Event(event_to_map, post_payload)
    event_map = EventMap(event_dispatch, [event_1_to_watch, event_2_to_watch], event_to_post, '')
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])

    # Test
    post_event(event_to_watch_1, {})
    post_event(event_to_watch_2, mapping_payload)

    # Verify
    time.sleep(0.2)

    # Confirm event map is not watching any more events.
    verify_events_to_watch(event_map, [])

    # Confirm mapped event and map triggered event were generated.
    validate_received_event(handler1, event_to_map, post_payload)
    validate_received_event(handler1, EventMapEvent.MAPPING_TRIGGERED, {})

    # Confirm event map is no longer registered for events that were watched.
    validate_handler_not_registered_for_event(event_map.on_event, event_to_watch_1)
    validate_handler_not_registered_for_event(event_map.on_event, event_to_watch_2)


def test_on_event__when_all_watched_events_already_occurred():
    # Objective:sss
    # Mapped event is not generated.

    global handler1

    # Setup
    event_map = create_event_map_with_no_payload([event_to_watch_1, event_to_watch_2], event_to_map)
    post_event(event_to_watch_1, {})
    post_event(event_to_watch_2, {})

    # Confirm event map is not watching any more events.
    time.sleep(0.2)
    verify_events_to_watch(event_map, [])

    register(handler1, [event_to_map])

    # Test
    post_event(event_to_watch_1, {})
    post_event(event_to_watch_2, {})

    # Verify
    time.sleep(0.2)
    validate_event_not_received(handler1, event_to_map)


def create_event_map_with_no_payload(events_to_watch: [str], event_to_post: str):
    global event_dispatch

    events_to_map = [Event(event, {}) for event in events_to_watch]
    event_to_post = Event(event_to_post, {})
    return EventMap(event_dispatch, events_to_map, event_to_post, '')


def verify_events_to_watch(event_map: EventMap, events_to_watch: [str]):
    assert len(event_map.events_to_watch) == len(events_to_watch)
    for event in events_to_watch:
        assert event in event_map.events_to_watch
