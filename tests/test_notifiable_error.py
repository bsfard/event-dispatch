import time

from eventdispatch import NotifiableError, EventDispatch
from eventdispatch.core import EventDispatchManager
from helper import EventHandler, register_handler_for_event, validate_received_event

event_dispatch: EventDispatch
handler: EventHandler


def setup_module():
    global event_dispatch

    event_dispatch = EventDispatchManager().default_dispatch
    event_dispatch.toggle_event_logging(True)


def setup_function():
    global event_dispatch, handler

    event_dispatch.clear_event_log()
    event_dispatch.clear_registered_handlers()
    event_dispatch.log_event_if_no_handlers = True

    handler = EventHandler()


def teardown_function():
    pass


def teardown_module():
    global event_dispatch
    event_dispatch.toggle_event_logging(False)


TEST_ERROR1 = 'error1'
TEST_ERROR2 = 'error2'
TEST_KEY = 'key'
TEST_VALUE = 'value'
TEST_ERROR_MESSAGE = 'test error message'

SOME_OTHER_ERROR = 'some_other_error'


class ErrorNotInPayloadError(NotifiableError):
    def __init__(self):
        message = TEST_ERROR_MESSAGE
        error = TEST_ERROR1
        payload = {
            TEST_KEY: TEST_VALUE
        }
        super().__init__(message, error, payload)


class ErrorInPayloadError(NotifiableError):
    def __init__(self):
        message = TEST_ERROR_MESSAGE
        error = TEST_ERROR2
        payload = {
            TEST_KEY: TEST_VALUE,
            'error': SOME_OTHER_ERROR
        }
        super().__init__(message, error, payload)


def test_notifiable_error__when_error_not_in_payload():
    # Objective:
    # Event name is the error type, and payload has a key 'error' with value set to error type.

    # Setup
    global handler
    register_handler_for_event(handler, TEST_ERROR1)
    expected_payload = {
        TEST_KEY: TEST_VALUE,
        'error': TEST_ERROR1,
        'message': TEST_ERROR_MESSAGE
    }

    # Test
    try:
        raise ErrorNotInPayloadError()
    except ErrorNotInPayloadError:
        pass

    # Verify
    time.sleep(0.1)
    validate_received_event(handler, TEST_ERROR1, expected_payload)


def test_notifiable_error__when_error_in_payload():
    # Objective:
    # Event name is the error type, and payload has a key 'error' with same value that was set there before.

    # Setup
    global handler
    register_handler_for_event(handler, TEST_ERROR2)
    expected_payload = {
        TEST_KEY: TEST_VALUE,
        'error': SOME_OTHER_ERROR,
        'message': TEST_ERROR_MESSAGE
    }

    # Test
    try:
        raise ErrorInPayloadError()
    except ErrorInPayloadError:
        pass

    # Verify
    time.sleep(0.1)
    validate_received_event(handler, TEST_ERROR2, expected_payload)
