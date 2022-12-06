import pytest

from eventdispatch import Data, InvalidDataError, MissingKeyError


def setup_module():
    pass


def setup_function():
    pass


def teardown_function():
    pass


def teardown_module():
    pass


def test_init__when_data_is_none():
    # Objective:
    # Data object creation is not allowed, exception is thrown.

    # Setup
    data = None

    # Test
    try:
        Data(data)
        pytest.fail('Expected to get exception')
    except InvalidDataError:
        pass

    # Verify
    # (none)


def test_init__when_data_is_empty_dict():
    # Objective:
    # Data object creation is allowed with an empty dictionary.

    # Setup
    data = {}

    # Test
    d = Data(data)

    # Verify
    assert d.dict == data
    assert d.json == '{}'


def test_get__when_raw_data_is_empty_dict():
    # Objective:
    # Get call fails since there's no key.

    # Setup
    data = {}
    d = Data(data)

    # Test
    try:
        d.get('key')
        pytest.fail('Expected to get exception')
    except MissingKeyError:
        pass

    # Verify
    # (none)


def test_get__when_have_raw_data__key_not_exist():
    # Objective:
    # Get call fails since there's no key.

    # Setup
    data = {
        'key': 'value'
    }
    d = Data(data)

    # Test
    try:
        d.get('another_key')
        pytest.fail('Expected to get exception')
    except MissingKeyError:
        pass

    # Verify
    # (none)


def test_get__when_have_raw_data__key_exists():
    # Objective:
    # Get call succeeds, and value for key is retrieved.

    # Setup
    data = {
        'key': 'value'
    }
    data_json = '{"key": "value"}'
    d = Data(data)

    # Test
    value = d.get('key')

    # Verify
    assert value == data['key']
    assert d.dict == data
    assert d.json == data_json


class DataSubclassWithProperties(Data):
    def __init__(self, key: str, payload: dict):
        super().__init__({
            'key': key,
            'payload': payload
        })

    @property
    def key(self) -> str:
        return self.get('key')

    @property
    def payload(self) -> dict:
        return self.get('payload')

    @property
    def name(self) -> str:
        return self.get('name', self.payload)


def test_get__when_subclass__have_properties():
    # Objective:
    # Properties are accessible and return the right data.

    # Setup
    key = 'value'
    payload = {
        'name': 'Bob'
    }
    data_subclass = DataSubclassWithProperties(key, payload)

    # Test
    # (none)

    # Verify
    assert data_subclass.key == key
    assert data_subclass.payload == payload
    assert data_subclass.name == 'Bob'


class DataSubclassSubclassWithProperty(DataSubclassWithProperties):
    def __init__(self, country):
        key = 'value'
        payload = {
            'name': 'Bob',
            'country': country
        }
        super().__init__(key, payload)

    @property
    def country(self) -> str:
        return self.get('country', self.payload)


def test_get__when_2nd_subclass__both_have_properties():
    # Objective:
    # Properties from both subclasses are accessible and return the right data.

    # Setup
    country = 'usa'
    data_subclass = DataSubclassSubclassWithProperty(country)
    data_subclass_json = '{"key": "value", "payload": {"name": "Bob", "country": "' + country + '"}}'

    # Test
    # (none)

    # Verify
    assert data_subclass.key == 'value'
    assert data_subclass.name == 'Bob'
    assert data_subclass.country == country
    assert data_subclass.json == data_subclass_json


def test_get__when_subclass__have_properties__data_passed_in__key_exists():
    # Objective:
    # Get call succeeds, and value for key is retrieved from passed in data instead of raw data.

    # Setup
    key = 'value'
    payload = {
        'name': 'Alice'
    }
    data_subclass = DataSubclassWithProperties(key, payload)

    # Test
    value = data_subclass.get('name', payload)

    # Verify
    assert value == payload['name']


class DataSubclassNoProperties(Data):
    def __init__(self):
        super().__init__({
            'key': 'value',
            'num': 50
        })


def test_subclass__when_no_additional_params():
    # Objective:
    # Subclass is created.

    # Setup

    # Test
    cls = DataSubclassNoProperties()

    # Verify
    value = cls.get('key')
    num = cls.get('num')

    assert value == 'value'
    assert num == 50
