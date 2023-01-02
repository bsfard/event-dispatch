# event-dispatch

A mechanism to generate, register for, and receive events in your app without the need of a local or remote messaging
service.

## Key points

- Events are generate and received within your app (process) only
- Events can contain an optional payload (key/value dictionary)
- Each event has a name (type), an ID, and a time stamp
- You can register (and unregister) for one or more events at a time
- You can register for all events
- Event registrations are NOT persisted (will be cleared when your app restarts)
- If you subclass ```NotifiableError``` for your custom exceptions, error events will be generated each time your
  exceptions are raised
- You can use a ```Properties``` object to store (and share) global-level info within your app

## High-level steps

1. Implement a method that will be called when desired events occur
2. Register for desired events
3. Generate an event

## Python Versions
Tested with: 3.7, 3.8, 3.9, 3.10, 3.11

## Sections
- [To run demo](#to-run-demo)
- [To install package](#to-install-package)
- [How to...](#how-to)
- [Design tips/considerations](#design-tipsconsiderations)
- [Troubleshooting](#troubleshooting)

## To run demo

```shell
git clone https://github.com/bsfard/event-dispatch
cd demo
PYTHONPATH=../ python run_workers
```

## To install package

### using pip

```shell
# Latest version
pip install git+https://github.com/bsfard/event-dispatch.git

# Specific version
pip install git+https://github.com/bsfard/event-dispatch.git@v0.0.4
```

### using requirements file

```shell
# Add to requirements file:

# Latest version
eventdispatch@ git+https://github.com/bsfard/event-dispatch.git

# Specific version
eventdispatch@ git+https://github.com/bsfard/event-dispatch.git@v0.0.4
```

## How to

- [Receive an event](#receive-an-event)
- [Register for events](#register-for-events)
- [Generate an event](#generate-an-event)
- [Unregister from events](#unregister-from-events)
- [Create custom exception (that will generate error event)](#create-custom-exception-that-will-generate-error-event)
- [Create event names as Enum with namespace](#create-event-names-as-enum-with-namespace)
- [Create a property](#create-a-property)

### Receive an event

```python
from eventdispatch import Event


def on_my_events(event: Event):
    print(f"Got event: '{event.name}', with payload '{event.payload}'")
```

### Register for events

```python
from eventdispatch import Event, register_for_events


def on_my_events(event: Event):
    print(f"Got event: '{event.name}', with payload '{event.payload}'")


# Specified events
register_for_events(on_my_events, ['event1', 'event2'])

# All events
register_for_events(on_my_events, [])
```

### Generate an event

```python
from eventdispatch import post_event

# No payload
post_event('event1')

# With payload
post_event('event2', {
    'some_key': 'some_value'
})
```

### Unregister from events

```python
from eventdispatch import Event, unregister_from_events


def on_my_events(event: Event):
    print(f"Got event: '{event.name}', with payload '{event.payload}'")


# Specified events
unregister_from_events(on_my_events, ['event1', 'event2'])

# All events
unregister_from_events(on_my_events, [])
```

### Create custom exception (that will generate error event)

```python
from eventdispatch import NotifiableError


class InvalidValue(NotifiableError):
    def __init__(self, value: str):
        message = f"Value provided '{value}' is not valid"
        error = 'invalid_value'
        payload = {
            'value': value
        }
        super().__init__(message, error, payload)
```

### Create event names as Enum with namespace

```python
from eventdispatch import NamespacedEnum, post_event


class MyEvents(NamespacedEnum):
    EVENT1 = 'event1'
    EVENT2 = 'event2'

    def get_namespace(self) -> str:
        return 'my_parent'


# Generate event
post_event(MyEvents.EVENT1)

# Event name received: 'my_parent.event1'
```

### Create a property

```python
from eventdispatch import Properties, PropertyNotSetError

# Set property (that cannot be modified)
Properties.set('MY_PROPERTY', 100)

# Set property (that will not be set/changed if already set)
Properties.set('ANOTHER_PROPERTY', 100, is_skip_if_exists=True)

# Set property (that can be modified)
Properties.set('ANOTHER_PROPERTY', 100, is_mutable=True)

try:
    my_property = Properties.get('MY_PROPERTY')
except PropertyNotSetError:
    print('Occurs if you forgot to set property before accessing it')

```

## Design tips/considerations

Events typically (but don't always have to) represent an activity that occurred. It is therefore preferred to define
event names that are in past tense.

```shell
# Examples of "ok" (but not great) event names:
processing
starting
need_file

# Examples of better (preferred) event names:
processing_started
app_started
could_not_find_file

# Event names can also include extra text that can be used (by your code) as namespace:
engine.processing_started
app.started
module.started
module.parser.could_not_find_file
error.module.parser.could_not_find_file
```

Event payload is a dictionary that can have whatever schema of data you want, including nested dictionaries. This can be
useful to collect and add data (in the moment) that would otherwise be difficult to fetch or require coupling across
components (after an operation).

Events are generally consider to be "cheap" especially if no one is registered for them. So it's usually beneficial to
generate an event when key/interesting/epic steps in your application occur. When you generate an event in such a way,
think about what information would be useful/interesting to a potential recipient of your event. Here are some examples
of possible events with possible useful payloads:

```python
from eventdispatch import Event, post_event

post_event('downloaded_file', {
    'path_to_file': '/home/user/temp/some_file.txt'
})

post_event('user_added', {
    'id': 123,
    'name': 'Jane Smith',
    'age': 30
})

post_event('calculation_error', {
    'inputs': [5, 10, -3],
    'instructions': None,
})

```

## Troubleshooting

With event-driven development, the most common problem is "nothing happens."  When this happens here are possible
mistakes to check:

- Did you register for the event of interest? If not, it will never be sent to you.
- Was the event generated?
- Did you implement your handler that will get the event to actually do something?

To help with troubleshooting, at your app level, register for all events, and log received events. This will be very
helpful throughout your development process.
