import time

from eventdispatch import NotifiableError, EventDispatch
from test_helper import TestEventHandler, register_handler_for_event, validate_received_event

handler: TestEventHandler


def setup_module():
    EventDispatch().toggle_event_logging(True)


def setup_function():
    global handler

    EventDispatch().clear_event_log()
    EventDispatch().clear_registered_handlers()
    EventDispatch().log_event_if_no_handlers = True

    handler = TestEventHandler()


def teardown_function():
    pass


def teardown_module():
    EventDispatch().toggle_event_logging(False)


TEST_ERROR1 = 'error1'
TEST_ERROR2 = 'error2'
TEST_KEY = 'key'
TEST_VALUE = 'value'
TEST_ERROR_MESSAGE = 'test error message'

SOME_OTHER_ERROR = 'some_other_error'


class TestErrorNotInPayloadError(NotifiableError):
    def __init__(self):
        message = TEST_ERROR_MESSAGE
        error = TEST_ERROR1
        payload = {
            TEST_KEY: TEST_VALUE
        }
        super().__init__(message, error, payload)


class TestErrorInPayloadError(NotifiableError):
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
    register_handler_for_event(handler, TEST_ERROR1)
    expected_payload = {
        TEST_KEY: TEST_VALUE,
        'error': TEST_ERROR1,
        'message': TEST_ERROR_MESSAGE
    }

    # Test
    try:
        raise TestErrorNotInPayloadError()
    except TestErrorNotInPayloadError:
        pass

    # Verify
    time.sleep(0.1)
    validate_received_event(handler, TEST_ERROR1, expected_payload)


def test_notifiable_error__when_error_in_payload():
    # Objective:
    # Event name is the error type, and payload has a key 'error' with same value that was set there before.

    # Setup
    register_handler_for_event(handler, TEST_ERROR2)
    expected_payload = {
        TEST_KEY: TEST_VALUE,
        'error': SOME_OTHER_ERROR,
        'message': TEST_ERROR_MESSAGE
    }

    # Test
    try:
        raise TestErrorInPayloadError()
    except TestErrorInPayloadError:
        pass

    # Verify
    time.sleep(0.1)
    validate_received_event(handler, TEST_ERROR2, expected_payload)
