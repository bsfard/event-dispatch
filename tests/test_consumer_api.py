from queue import Queue

from eventdispatch import Event, NamespacedEnum, post_event, register_for_events, unregister_from_events


class ConsumerEvent(NamespacedEnum):
    DID_SOMETHING = 'did_something'

    def get_namespace(self) -> str:
        return 'consumer'


def test_consumer_can_import_public_api_and_receive_event():
    received_events = Queue()

    def on_event(event: Event):
        received_events.put(event)

    register_for_events(on_event, [ConsumerEvent.DID_SOMETHING])

    try:
        post_event(ConsumerEvent.DID_SOMETHING, {'id': 123})
        event = received_events.get(timeout=1)
    finally:
        unregister_from_events(on_event, [ConsumerEvent.DID_SOMETHING])

    assert event.name == 'consumer.did_something'
    assert event.payload == {'id': 123}
