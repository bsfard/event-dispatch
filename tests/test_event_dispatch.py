import time
from typing import Any, Dict

from eventdispatch import EventDispatch
from eventdispatch.core import EventDispatchEvent, EventDispatchManager
from helper import EventHandler, validate_test_handler_registered_for_event, \
    validate_handler_registered_for_all_events, validate_event_log_count, validate_expected_handler_count, \
    register_handler_for_event, register, validate_received_events

event_dispatch: EventDispatch
handler1: EventHandler
handler2: EventHandler
all_event_handler: EventHandler


def setup_module():
    global event_dispatch

    event_dispatch = EventDispatchManager().default_dispatch
    event_dispatch.toggle_event_logging(True)


def setup_function():
    global handler1, handler2, all_event_handler

    event_dispatch.clear_event_log()
    event_dispatch.clear_registered_handlers()
    event_dispatch.log_event_if_no_handlers = True

    handler1 = EventHandler()
    handler2 = EventHandler()
    all_event_handler = EventHandler()


def teardown_function():
    pass


def teardown_module():
    event_dispatch.toggle_event_logging(False)


def test_register__when_not_registered():
    # Objective:
    # Handler is registered.

    # Setup
    test_event = 'test_event'

    # Test
    register(handler1, [test_event])

    # Verify
    validate_expected_handler_count(1)
    validate_test_handler_registered_for_event(handler1, test_event)
    validate_event_log_count(1)


def test_register__when_registered_for_different_event():
    # Objective:
    # Handler is now registered for both events.

    # Setup
    previous_event = 'previous_event'
    test_event = 'test_event'
    register_handler_for_event(handler1, previous_event)

    # Test
    register(handler1, [test_event])

    # Verify
    validate_expected_handler_count(2)
    validate_test_handler_registered_for_event(handler1, test_event)
    validate_event_log_count(2)


def test_register__when_already_registered_for_event():
    # Objective:
    # Handler is still registered for event, and only once (nothing is changed).

    # Setup
    test_event = 'test_event'
    register_handler_for_event(handler1, test_event)

    # Test
    register(handler1, [test_event])

    # Verify
    validate_expected_handler_count(1)
    validate_test_handler_registered_for_event(handler1, test_event)
    validate_event_log_count(1)


def test_register__when_multiple_events():
    # Objective:
    # Handler is registered for all events being registered in one call.

    # Setup
    test_event1 = 'test_event1'
    test_event2 = 'test_event2'

    # Test
    register(handler1, [test_event1, test_event2])

    # Verify
    validate_expected_handler_count(2)
    validate_test_handler_registered_for_event(handler1, test_event1)
    validate_test_handler_registered_for_event(handler1, test_event2)
    validate_event_log_count(1)


def test_register__when_for_all_events_when_not_yet_registered():
    # Objective:
    # Handler is registered for "all events".

    # Setup
    # (none)

    # Test
    register(all_event_handler, [])

    # Verify
    validate_expected_handler_count(1)
    validate_handler_registered_for_all_events(all_event_handler)
    validate_event_log_count(1)


def test_register__when_for_all_events_when_registered_for_event():
    # Objective:
    # Handler is still registered for event, and now also registered for "all events".

    # Setup
    test_event = 'test_event'
    register_handler_for_event(handler1, test_event)

    # Test
    register(all_event_handler, [])

    # Verify
    validate_expected_handler_count(2)
    validate_test_handler_registered_for_event(handler1, test_event)
    validate_handler_registered_for_all_events(all_event_handler)
    validate_event_log_count(2)


def test_register__confirm_registration_event_is_posted():
    # Objective:
    # Event is posted when handler is registered, with proper payload.

    # Setup
    register_handler_for_event(all_event_handler)
    time.sleep(0.1)
    validate_received_events(all_event_handler, [EventDispatchEvent.HANDLER_REGISTERED],
                             is_ignore_registration_event=False)
    test_event = 'test_event'

    # Test
    register(handler1, [test_event])

    # Verify
    time.sleep(0.1)
    validate_received_events(all_event_handler, [EventDispatchEvent.HANDLER_REGISTERED],
                             is_ignore_registration_event=False)


def test_register__when_event_with_wildcard__in_end():
    # Objective:

    # Setup
    test_event = 'test*'

    # Test
    register(handler1, [test_event])

    # Verify
    validate_expected_handler_count(1)
    validate_test_handler_registered_for_event(handler1, test_event)
    validate_event_log_count(1)


def test_post__when_no_registered_handlers_for_event():
    # Objective:
    # No event is propagated.

    # Setup
    test_event = 'test_event'
    event_dispatch.log_event_if_no_handlers = False
    validate_event_log_count(0)

    # Test
    post_event(test_event)

    # Verify
    validate_expected_handler_count(0)
    validate_event_log_count(0)


def test_post_event__when_no_registered_handlers_but_have_all_event_registered_handler():
    # Objective:
    # One event is propagated (to all-event registered handler).
    # All-event registered handler received the event.

    # Setup
    test_event = 'test_event'
    register_handler_for_event(all_event_handler)

    # Test
    post_event(test_event)

    # Verify
    validate_event_log_count(2)
    time.sleep(0.1)
    validate_received_events(all_event_handler, [test_event])


def test_post_event_when_registered_handler_for_event():
    # Objective:
    # One event is propagated (to registered handler).
    # Registered handler received the event.

    # Setup
    test_event = 'test_event'
    register_handler_for_event(handler1, test_event)

    # Test
    post_event(test_event)

    # Verify
    validate_event_log_count(2)
    time.sleep(0.1)
    validate_received_events(handler1, [test_event])


def test_post_event__when_registered_handler_and_different_all_event_registered_handler():
    # Objective:
    # Two events are propagated (to registered handler and all-event handler).
    # Both handlers received events.

    # Setup
    test_event = 'test_event'
    register_handler_for_event(handler1, test_event)
    register_handler_for_event(all_event_handler)

    # Test
    post_event(test_event)

    # Verify
    validate_event_log_count(3)
    time.sleep(0.1)
    validate_received_events(handler1, [test_event])
    validate_received_events(all_event_handler, [test_event])


def test_post_event__when_same_registered_and_all_event_registered_handlers():
    # Objective:
    # One event is propagated (to registered handler).
    # Registered handler received the event.

    # Setup
    test_event = 'test_event'
    register_handler_for_event(handler1, test_event)
    register_handler_for_event(handler1)

    validate_expected_handler_count(2)
    validate_event_log_count(2)

    # Test
    post_event(test_event)

    # Verify
    validate_event_log_count(3)
    time.sleep(0.1)
    validate_received_events(handler1, [test_event])


def test_post_event__when_two_registered_handlers_for_same_event():
    # Objective:
    # Two events are propagated (one to each registered handler).

    # Setup
    test_event = 'test_event'
    register_handler_for_event(handler1, test_event)
    register_handler_for_event(handler2, test_event)

    # Test
    post_event(test_event)

    # Verify
    validate_event_log_count(3)
    time.sleep(0.1)
    validate_received_events(handler1, [test_event])
    validate_received_events(handler2, [test_event])


def test_post_event__when_registered_handler_for_different_event():
    # Objective:
    # No event is propagated.

    # Setup
    test_event1 = 'test_event1'
    register_handler_for_event(handler1, test_event1)

    test_event2 = 'test_event2'

    # Test
    post_event(test_event2)

    # Verify
    validate_event_log_count(2)
    validate_received_events(handler1, [])


def test_unregister__when_not_registered():
    # Objective:
    # Previous handlers remain intact.

    # Setup
    test_event = 'test_event'
    register_handler_for_event(handler1, test_event)

    # Test
    unregister(handler2, [test_event])

    # Verify
    validate_event_log_count(1)
    validate_test_handler_registered_for_event(handler1, test_event)
    validate_received_events(handler1, [])


def test_unregister__when_registered__multiple_events():
    # Objective:
    # Registrations are removed.

    # Setup
    test_event1 = 'test_event1'
    test_event2 = 'test_event2'
    register(handler1, [test_event1, test_event2])

    # Test
    unregister(handler1, [test_event1, test_event2])

    # Verify
    validate_event_log_count(2)
    validate_expected_handler_count(0)


def test_unregister__when_registered_for_only_one_of_the_events():
    # Objective:
    # Registration that exists for event is removed.

    # Setup
    test_event1 = 'test_event1'
    test_event2 = 'test_event2'
    register(handler1, [test_event1, test_event2])

    test_event3 = 'test_event3'

    # Test
    unregister(handler1, [test_event2, test_event3])

    # Verify
    validate_event_log_count(2)
    validate_test_handler_registered_for_event(handler1, test_event1)
    validate_expected_handler_count(1)


def test_unregister__when_registered_for_different_event():
    # Objective:
    # Registration for the different event is intact.

    # Setup
    test_event1 = 'test_event1'
    register(handler1, [test_event1])

    test_event2 = 'test_event2'

    # Test
    unregister(handler1, [test_event2])

    # Verify
    validate_event_log_count(1)
    validate_test_handler_registered_for_event(handler1, test_event1)
    validate_expected_handler_count(1)


def test_unregister__confirm_unregistration_event_is_posted():
    # Objective:
    # Event is posted when handler is unregistered, with proper payload.

    # Setup
    test_event = 'test_event'
    register(handler1, [test_event])
    register_handler_for_event(all_event_handler)

    # Test
    unregister(handler1, [test_event])

    # Verify
    time.sleep(0.1)
    validate_received_events(all_event_handler,
                             [EventDispatchEvent.HANDLER_REGISTERED, EventDispatchEvent.HANDLER_UNREGISTERED],
                             is_ignore_registration_event=False)


def unregister(handler: EventHandler, events: [str]):
    event_dispatch.unregister(handler.on_event, events)


def post_event(event: str, payload: Dict[str, Any] = None):
    event_dispatch.post_event(event, payload)
