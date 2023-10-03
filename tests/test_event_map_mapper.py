import time

import pytest

from eventdispatch.core import EventMapManager, EventDispatch, EventDispatchManager, Event, InvalidMappingEventsError, \
    DuplicateMappingError, MappingNotFoundError, EventMapEvent, post_event
from helper import EventHandler, validate_received_events, register_handler_for_event

event_dispatch: EventDispatch
handler1: EventHandler
event_map_manager: EventMapManager

event_to_watch_1 = 'event_1'
event_to_watch_2 = 'event_2'
event_to_map = 'event_3'


def setup_module():
    global event_dispatch
    event_dispatch = EventDispatchManager().default_dispatch
    event_dispatch.toggle_event_logging(True)


def setup_function():
    global handler1, event_map_manager

    event_dispatch.clear_event_log()
    event_dispatch.log_event_if_no_handlers = True

    handler1 = EventHandler()
    event_map_manager = EventMapManager(event_dispatch)


def teardown_function():
    pass


def teardown_module():
    event_dispatch.toggle_event_logging(False)


@pytest.mark.parametrize('events_to_watch, event_to_post', [
    (
            [], 'test_event'
    ),
    (
            None, 'test_event'
    ),
    (
            [event_to_watch_1], None
    ),
])
def test_map_events__when_invalid_events(events_to_watch: [str], event_to_post: str):
    # Objective:
    # Exception is thrown.

    # Setup
    events_to_map = []
    if events_to_watch:
        for event_to_watch in events_to_watch:
            events_to_map.append(Event(event_to_watch, {}))

    if event_to_post:
        event_to_post = Event(event_to_post, {})

    # Test
    try:
        event_map_manager.map_events(events_to_map, event_to_post)
        pytest.fail('Expected to get exception')
    except InvalidMappingEventsError:
        pass

    # Verify
    # (none)


@pytest.mark.parametrize('events_to_watch', [
    [event_to_watch_1, event_to_watch_2],
    [event_to_watch_1]
])
def test_map_events__no_payload(events_to_watch: [str]):
    # Objective:
    # Event map is created.
    # Event is posted for map created.

    # Setup
    events = []
    for event_to_watch in events_to_watch:
        events.append(Event(event_to_watch, {}))
    events_to_map = events
    event_to_post = Event(event_to_map, {})
    register_handler_for_event(handler1, EventMapEvent.MAPPING_CREATED.namespaced_value)

    # Test
    event_map_manager.map_events(events_to_map, event_to_post)

    # Verify
    time.sleep(0.2)
    validate_event_map_exists(events_to_map, event_to_post)
    validate_received_events(handler1, [EventMapEvent.MAPPING_CREATED.namespaced_value])


def test_map_events__when_duplicate_mapping__no_reset():
    # Objective:
    # Exception is thrown.

    # Setup
    events_to_map = [
        Event(event_to_watch_1, {}),
    ]
    event_to_post = Event(event_to_map, {})
    event_map_manager.map_events(events_to_map, event_to_post)
    validate_event_map_exists(events_to_map, event_to_post)

    # Test
    try:
        event_map_manager.map_events(events_to_map, event_to_post)
        pytest.fail('Expected to get exception')
    except DuplicateMappingError:
        pass

    # Verify
    # (none)


def test_map_events__when_duplicate_mapping__with_reset():
    # Objective:
    # Event map is reset.
    # Event is posted for map reset.

    # Setup
    events_to_map = [
        Event(event_to_watch_1, {}),
    ]
    event_to_post = Event(event_to_map, {})
    event_map_manager.map_events(events_to_map, event_to_post)
    validate_event_map_exists(events_to_map, event_to_post)

    # Test
    try:
        event_map_manager.map_events(events_to_map, event_to_post, reset_if_exists=True)
    except DuplicateMappingError:
        pytest.fail('Did not expect to get exception')

    # Verify
    # (none)


@pytest.mark.parametrize('key', [
    '',
    None,
    'test_key'
])
def test_remove_event_map_by_key__when_key_not_exist(key: str):
    # Objective:
    # Exception is thrown if key is invalid or valid but not found.

    # Setup
    # (none)

    # Test
    try:
        event_map_manager.remove_event_map_by_key(key)
        pytest.fail('Expected to get exception')
    except MappingNotFoundError:
        pass

    # Verify
    # (none)


def test_remove_event_map_by_key__when_key_exists():
    # Objective:
    # Event map is removed.
    # Event is posted for map removal.

    # Setup
    events_to_map = [
        Event(event_to_watch_1, {}),
    ]
    event_to_post = Event(event_to_map, {})
    event_map_manager.map_events(events_to_map, event_to_post)
    validate_event_map_exists(events_to_map, event_to_post)
    register_handler_for_event(handler1, EventMapEvent.MAPPING_REMOVED.namespaced_value)

    key = event_map_manager.build_key(events_to_map, event_to_post)

    # Test
    event_map_manager.remove_event_map_by_key(key)

    # Verify
    time.sleep(0.2)
    validate_event_map_not_exist(events_to_map, event_to_post)
    validate_received_events(handler1, [EventMapEvent.MAPPING_REMOVED.namespaced_value])


@pytest.mark.parametrize('key_exists', [
    True,
    False
])
def test_on_event__when_event_is_mapping_triggered(key_exists: bool):
    # Objective:
    # Event map is removed when key exists, otherwise nothing is removed when key doesn't exist.
    # Testing is done via direct call to "on_event" method.

    # Setup
    events_to_map = [
        Event(event_to_watch_1, {}),
    ]
    event_to_post = Event(event_to_map, {})
    event_map_manager.map_events(events_to_map, event_to_post)
    validate_event_map_exists(events_to_map, event_to_post)

    key = '' if not key_exists else event_map_manager.build_key(events_to_map, event_to_post)

    test_event = Event(EventMapEvent.MAPPING_TRIGGERED.namespaced_value, {'key': key})

    # Test
    event_map_manager.on_event(test_event)

    # Verify
    if key_exists:
        validate_event_map_not_exist(events_to_map, event_to_post)
    else:
        validate_event_map_exists(events_to_map, event_to_post)


def test__when_have_event_map__mapping_triggered():
    # Objective:
    # Event map is not altered.
    # Testing is done via event (that is sent to "on_event" method).

    # Setup
    events_to_map = [
        Event(event_to_watch_1, {}),
    ]
    event_to_post = Event(event_to_map, {})
    event_map_manager.map_events(events_to_map, event_to_post)
    validate_event_map_exists(events_to_map, event_to_post)

    key = event_map_manager.build_key(events_to_map, event_to_post)

    # Test
    post_event(EventMapEvent.MAPPING_TRIGGERED, {'key': key})

    # Verify
    time.sleep(0.2)
    validate_event_map_not_exist(events_to_map, event_to_post)


def validate_event_map_exists(events_to_map: [Event], event_to_post: Event):
    key = event_map_manager.build_key(events_to_map, event_to_post)
    assert key in event_map_manager.event_maps


def validate_event_map_not_exist(events_to_map: [Event], event_to_post: Event):
    key = event_map_manager.build_key(events_to_map, event_to_post)
    assert key not in event_map_manager.event_maps
