import time

import pytest

from eventdispatch import Event
from eventdispatch.core import EventMap, EventDispatch, EventDispatchManager, post_event, InvalidMappingEventsError, \
    EventMapEvent
from helper import EventHandler, register, validate_received_events, get_event_log_count, validate_event_log_count, \
    validate_handler_not_registered_for_event, validate_event_not_received, validate_handler_registered_for_event

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
    global handler1

    event_dispatch.clear_event_log()
    event_dispatch.clear_registered_handlers()
    event_dispatch.log_event_if_no_handlers = True

    handler1 = EventHandler()


def teardown_function():
    pass


def teardown_module():
    event_dispatch.toggle_event_logging(False)


@pytest.mark.parametrize('events_to_watch', [None, '', [], [None, None]])
def test_constructor__when_no_events_to_watch(events_to_watch: [Event]):
    # Objective:
    # Exception is thrown.

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


def test_constructor__when_no_payload():
    # Objective:
    # Event map is watching for expected events.
    # Event map is registered for each event to watch.

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


def test_on_event__when_not_last_event():
    # Objective:
    # Events being watched are updated (1 less event being watched).
    # Events map does not generated mapped event.

    # Setup
    event_map = create_event_map([event_to_watch_1, event_to_watch_2], event_to_map)
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])
    expected_event_count = get_event_log_count()

    # Test
    post_event(event_to_watch_1, {})

    # Verify
    time.sleep(0.2)
    expected_event_count += 1
    verify_events_to_watch(event_map, [event_to_watch_2])
    validate_event_log_count(expected_event_count)


def test_on_event__when_repeat_event():
    # Objective:
    # Events being watched are not updated.
    # Events map does not generated mapped event.

    # Setup
    event_map = create_event_map([event_to_watch_1, event_to_watch_2], event_to_map)
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


def test_on_event__when_last_event():
    # Objective:
    # Events being watched are updated (no more events being watched).
    # Events map generates mapped event, and mapping-triggered event.
    # Event map unregistered from events being watched.

    # Setup
    event_map = create_event_map([event_to_watch_1, event_to_watch_2], event_to_map)
    verify_events_to_watch(event_map, [event_to_watch_1, event_to_watch_2])
    register(handler1, [event_to_map, EventMapEvent.MAPPING_TRIGGERED.namespaced_value])

    # Test
    post_event(event_to_watch_1, {})
    post_event(event_to_watch_2, {})

    # Verify
    time.sleep(0.2)

    # Confirm event map is not watching any more events.
    verify_events_to_watch(event_map, [])

    # Confirm mapped event and map triggered event were generated.
    validate_received_events(handler1, [event_to_map, EventMapEvent.MAPPING_TRIGGERED])

    # Confirm event map is no longer registered for events that were watched.
    validate_handler_not_registered_for_event(event_map.on_event, event_to_watch_1)
    validate_handler_not_registered_for_event(event_map.on_event, event_to_watch_2)


def test_on_event__when_all_watched_events_already_occurred():
    # Objective:
    # Mapped event is not generated.

    # Setup
    event_map = create_event_map([event_to_watch_1, event_to_watch_2], event_to_map)
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


def create_event_map(events_to_watch: [str], event_to_post: str):
    events_to_map = [Event(event, {}) for event in events_to_watch]
    event_to_post = Event(event_to_post, {})
    return EventMap(event_dispatch, events_to_map, event_to_post, '')


def verify_events_to_watch(event_map: EventMap, events_to_watch: [str]):
    assert len(event_map.events_to_watch) == len(events_to_watch)
    for event in events_to_watch:
        assert event in event_map.events_to_watch
