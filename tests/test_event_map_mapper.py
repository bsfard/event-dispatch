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


test_params__events_to_watch__expected_keys = [
    # One event, no payload.
    (
        [
            Event(event_to_watch_1, {}),
        ],
        'ca29afc0c6f152074f1bb35fb0f1c5a987f0938a4767639740f6169e96cea4ed'
    ),

    # One event, with payload.
    (
        [
            Event(event_to_watch_1, {'id': 5}),
        ],
        '2179092d98d47a016a99009c9cfa6f939cf33e93642c528480053df39a37767e'
    ),

    # Two events, no payload, one order.
    (
        [
            Event(event_to_watch_1, {}),
            Event(event_to_watch_2, {}),
        ],
        '73fe8cf3e1944372cd6bf424fc672a6ca621e90195c4084d6e9d77ce0113c1fa'
    ),

    # Two events, no payload, different order.
    (
        [
            Event(event_to_watch_2, {}),
            Event(event_to_watch_1, {}),
        ],
        '73fe8cf3e1944372cd6bf424fc672a6ca621e90195c4084d6e9d77ce0113c1fa'
    ),

    # Two events, one with payload, one order.
    (
        [
            Event(event_to_watch_1, {'id': 5}),
            Event(event_to_watch_2, {}),
        ],
        'dd02b72f92cfae8cf991e6478805b072f30c975ea93e3a794d1713483df97142'
    ),

    # Two events, one with payload, different order.
    (
        [
            Event(event_to_watch_2, {}),
            Event(event_to_watch_1, {'id': 5}),
        ],
        'dd02b72f92cfae8cf991e6478805b072f30c975ea93e3a794d1713483df97142'
    ),

    # Two events, payload, one order.
    (
        [
            Event(event_to_watch_1, {'id': 5}),
            Event(event_to_watch_2, {'name': 'mary', 'age': 10}),
        ],
        '3bea6bb39ac22ea37b905767bd93f3ca83f3fee2242480bd264039212be7f29c'
    ),

    # Two events, payload, different order.
    (
        [
            Event(event_to_watch_2, {'name': 'mary', 'age': 10}),
            Event(event_to_watch_1, {'id': 5}),
        ],
        '3bea6bb39ac22ea37b905767bd93f3ca83f3fee2242480bd264039212be7f29c'
    ),

]


@pytest.mark.parametrize('event_to_watch, expected_key', test_params__events_to_watch__expected_keys)
def test_build_key(event_to_watch: [Event], expected_key: str):
    # Objective:
    # Key is built correctly, given the specific inputs.

    # Setup
    # (none)

    # Test
    key = event_map_manager.build_key(event_to_watch)

    # Verify
    assert key == expected_key


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


@pytest.mark.parametrize('events_to_watch, expected_key', test_params__events_to_watch__expected_keys)
def test_map_events__no_payload(events_to_watch: [Event], expected_key: str):
    # Objective:
    # Event map is created.
    # Event is posted for map created.

    # Setup
    event_to_post = Event(event_to_map, {})

    register_handler_for_event(handler1, EventMapEvent.MAPPING_CREATED.namespaced_value)

    # Test
    key = event_map_manager.map_events(events_to_watch, event_to_post)

    # Verify
    time.sleep(0.2)
    validate_event_map_exists(events_to_watch)
    validate_received_events(handler1, [EventMapEvent.MAPPING_CREATED.namespaced_value])
    assert key == expected_key


def test_map_events__when_duplicate_mapping():
    # Objective:
    # Exception is thrown.

    # Setup
    events_to_map = [
        Event(event_to_watch_1, {}),
    ]
    event_to_post = Event(event_to_map, {})
    event_map_manager.map_events(events_to_map, event_to_post)
    validate_event_map_exists(events_to_map)

    # Test
    try:
        event_map_manager.map_events(events_to_map, event_to_post)
        pytest.fail('Expected to get exception')
    except DuplicateMappingError:
        pass

    # Verify
    # (none)


@pytest.mark.parametrize('events_to_watch, expected_key', [
    # One event, no payload.
    (
            [
                Event(event_to_watch_1, {}),
            ],
            'ca29afc0c6f152074f1bb35fb0f1c5a987f0938a4767639740f6169e96cea4ed'
    ),
])
def test_map_events__when_duplicate_mapping__with_ignore_if_exists(events_to_watch: [Event], expected_key: str):
    # Objective:
    # Event map is not created.
    # Event is not posted for map created.
    # Exception is NOT thrown

    # Setup
    event_to_post = Event(event_to_map, {})
    event_map_manager.map_events(events_to_watch, event_to_post)
    validate_event_map_exists(events_to_watch)

    # Test
    key = event_map_manager.map_events(events_to_watch, event_to_post, ignore_if_exists=True)

    # Verify
    assert key == expected_key


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
    validate_event_map_exists(events_to_map)
    register_handler_for_event(handler1, EventMapEvent.MAPPING_REMOVED.namespaced_value)

    key = event_map_manager.build_key(events_to_map)

    # Test
    event_map_manager.remove_event_map_by_key(key)

    # Verify
    time.sleep(0.2)
    validate_event_map_not_exist(events_to_map)
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
    validate_event_map_exists(events_to_map)

    key = '' if not key_exists else event_map_manager.build_key(events_to_map)

    test_event = Event(EventMapEvent.MAPPING_TRIGGERED.namespaced_value, {'key': key})

    # Test
    event_map_manager.on_event(test_event)

    # Verify
    if key_exists:
        validate_event_map_not_exist(events_to_map)
    else:
        validate_event_map_exists(events_to_map)


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
    validate_event_map_exists(events_to_map)

    key = event_map_manager.build_key(events_to_map)

    # Test
    post_event(EventMapEvent.MAPPING_TRIGGERED, {'key': key})

    # Verify
    time.sleep(0.2)
    validate_event_map_not_exist(events_to_map)


def validate_event_map_exists(events_to_map: [Event]):
    key = event_map_manager.build_key(events_to_map)
    assert key in event_map_manager.event_maps


def validate_event_map_not_exist(events_to_map: [Event]):
    key = event_map_manager.build_key(events_to_map)
    assert key not in event_map_manager.event_maps
