##############################################################################
# Taken from the cpython 3.11 source branch after the 3.11.10 release.
# It has been modified for vendored imports and to remove unused items.
##############################################################################
# """Supporting definitions for the Python regression tests."""

if __name__ != 'synapse.vendor.cpython.lib.test.support':
    raise ImportError('support must be imported from the test package')

import contextlib
import dataclasses
import functools
import os
import re
import stat
import sys
import sysconfig
import time
import types
import unittest
import warnings

__all__ = [
    # miscellaneous
    "run_with_tz",
    "LARGEST", "SMALLEST",
    ]

def run_with_tz(tz):
    def decorator(func):
        def inner(*args, **kwds):
            try:
                tzset = time.tzset
            except AttributeError:
                raise unittest.SkipTest("tzset required")
            if 'TZ' in os.environ:
                orig_tz = os.environ['TZ']
            else:
                orig_tz = None
            os.environ['TZ'] = tz
            tzset()

            # now run the function, resetting the tz on exceptions
            try:
                return func(*args, **kwds)
            finally:
                if orig_tz is None:
                    del os.environ['TZ']
                else:
                    os.environ['TZ'] = orig_tz
                time.tzset()

        inner.__name__ = func.__name__
        inner.__doc__ = func.__doc__
        return inner
    return decorator

def patch(test_instance, object_to_patch, attr_name, new_value):
    """Override 'object_to_patch'.'attr_name' with 'new_value'.

    Also, add a cleanup procedure to 'test_instance' to restore
    'object_to_patch' value for 'attr_name'.
    The 'attr_name' should be a valid attribute for 'object_to_patch'.

    """
    # check that 'attr_name' is a real attribute for 'object_to_patch'
    # will raise AttributeError if it does not exist
    getattr(object_to_patch, attr_name)

    # keep a copy of the old value
    attr_is_local = False
    try:
        old_value = object_to_patch.__dict__[attr_name]
    except (AttributeError, KeyError):
        old_value = getattr(object_to_patch, attr_name, None)
    else:
        attr_is_local = True

    # restore the value when the test is done
    def cleanup():
        if attr_is_local:
            setattr(object_to_patch, attr_name, old_value)
        else:
            delattr(object_to_patch, attr_name)

    test_instance.addCleanup(cleanup)

    # actually override the attribute
    setattr(object_to_patch, attr_name, new_value)


@functools.total_ordering
class _LARGEST:
    """
    Object that is greater than anything (except itself).
    """
    def __eq__(self, other):
        return isinstance(other, _LARGEST)
    def __lt__(self, other):
        return False

LARGEST = _LARGEST()

@functools.total_ordering
class _SMALLEST:
    """
    Object that is less than anything (except itself).
    """
    def __eq__(self, other):
        return isinstance(other, _SMALLEST)
    def __gt__(self, other):
        return False

SMALLEST = _SMALLEST()
