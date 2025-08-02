# ---------------------------------------------------------------------- #
# FILE: tests/mock_lldb.py
#
# DESCRIPTION:
# This module provides a centralized, robust set of mock objects that
# simulate the behavior of the LLDB API (e.g., lldb.SBValue, lldb.SBType).
# By centralizing the mocks here, all test files can share the same
# faithful simulation, ensuring consistency and simplifying maintenance.
# ---------------------------------------------------------------------- #

from unittest.mock import Mock


class MockSBValue:
    """
    A comprehensive mock for lldb.SBValue. It implements all methods
    required by our formatters and strategies to run in a test environment.
    """

    def __init__(self, value=None, children=None, is_pointer=False):
        self._value = value
        self._children = children if children else {}
        self._is_pointer = is_pointer

        # ----- Mock for the SBType object ----- #
        self._type_mock = Mock()
        self._type_mock.IsPointerType.return_value = self._is_pointer

        mock_fields = []
        for name in self._children.keys():
            mock_field = Mock()
            mock_field.GetName.return_value = name
            mock_fields.append(mock_field)

        self._type_mock.GetNumberOfFields.return_value = len(mock_fields)
        self._type_mock.GetFieldAtIndex.side_effect = lambda i: mock_fields[i]

        # ----- Mock for the SBAddress object ----- #
        self._addr_mock = Mock()
        self._addr_mock.GetFileAddress.return_value = id(self)

    def GetChildMemberWithName(self, name):
        return self._children.get(name)

    def GetValueAsUnsigned(self):
        # Simulates getting the address of a raw pointer.
        if isinstance(self._value, int):
            return self._value
        return id(self)

    def GetSummary(self):
        return str(self._value) if self._value is not None else ""

    def Dereference(self):
        return self

    def IsValid(self):
        return True

    def GetType(self):
        # This is now a method, as required by the LLDB API.
        return self._type_mock

    def GetAddress(self):
        return self._addr_mock


class MockSBValueContainer(MockSBValue):
    """A specialized mock for container types like std::vector."""

    def __init__(self, items):
        super().__init__()
        self._items = items

    def GetNumChildren(self):
        return len(self._items)

    def GetChildAtIndex(self, index):
        return self._items[index]

    def MightHaveChildren(self):
        return len(self._items) > 0
