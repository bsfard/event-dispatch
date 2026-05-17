from eventdispatch import Event


def test_from_dict__creates_new_event_with_same_name_and_payload():
    # Objective:
    # from_dict is a constructor convenience, not exact event deserialization.

    # Setup
    original_event = Event('test_event', {'name': 'Alice'})

    # Test
    new_event = Event.from_dict(original_event.dict)

    # Verify
    assert new_event.name == original_event.name
    assert new_event.payload == original_event.payload
    assert new_event.id != original_event.id
    assert new_event.time != original_event.time
