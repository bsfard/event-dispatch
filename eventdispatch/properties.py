from typing import Any

from eventdispatch import NotifiableError


class Properties:
    __instance = None
    __properties = {}

    def __new__(cls):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    @staticmethod
    def has(property_name: str) -> bool:
        return Properties().__has(property_name)

    def __has(self, property_name: str) -> bool:
        return property_name in self.__properties

    @staticmethod
    def get(property_name: str) -> Any:
        return Properties().__get(property_name)

    def __get(self, property_name: str) -> Any:
        try:
            p = self.__properties[property_name]
            return p.get('value')
        except KeyError:
            raise PropertyNotSetError(property_name)

    @staticmethod
    def set(property_name: str, value: Any, is_mutable=False, is_skip_if_exists=False):
        Properties().__set(property_name, value, is_mutable, is_skip_if_exists)

    def __set(self, property_name: str, value: Any, is_mutable=False, is_skip_if_exists=False):
        try:
            # Check if property exists.
            p = self.__properties[property_name]

            # Check if property should be skipped.
            if is_skip_if_exists:
                return

            # Check if property is allowed to be modified.
            if not p['is_mutable']:
                raise ImmutablePropertyModificationError(property_name, p['value'], value)

            # Update property.
            p['value'] = value
        except KeyError:
            # First time setting property.
            self.__properties[property_name] = {
                'value': value,
                'is_mutable': is_mutable
            }

    @staticmethod
    def get_list() -> [str]:
        return Properties().__get_list()

    def __get_list(self) -> [str]:
        return list(self.__properties.keys())


class PropertyNotSetError(NotifiableError):
    def __init__(self, property_name: str):
        message = f"Property '{property_name}' has not been set."
        error = 'property_not_set'
        payload = {
            'property': property_name
        }
        super().__init__(message, error, payload)


class ImmutablePropertyModificationError(NotifiableError):
    def __init__(self, property_name: str, current_value: Any, new_value: Any):
        message = f"Attempting to modify immutable property '{property_name}'"
        error = 'immutable_property_modification'
        payload = {
            'property': property_name,
            'current_value': current_value,
            'new_value': new_value
        }
        super().__init__(message, error, payload)
