import os
from contextlib import contextmanager
from typing import Any


@contextmanager
def set_environments(envs: dict[str, str]):
    """
    Set the given environments before testing
    remove them once the test is over
    """
    os.environ.update(envs)
    try:
        yield
    finally:
        for key in envs:
            del os.environ[key]


@contextmanager
def check_error(expected: Any):
    """
    If happens that we want the program to raise an error.
    In this case, `expected` should be of class Exception.
    This function checks that this is the case,
    and that `expected` matches `err`

    This is used as a context manager. It takes an expected result
    `expected`, and check if it corresponds to the raised error, if any

    **usage example**
    >>> import pytest
    >>>
    >>> def square(i: int) -> int:
    >>>     if not isinstance(i, int):
    >>>         raise ValueError("int expected")
    >>>     return i * i
    >>>
    >>> @pytest.mark.parametrize(
    >>>     "input,expected",
    >>>     [(2, 4), (3, 9), ("r", ValueError("int expected"))]
    >>> )
    >>> def test_square(input, expected):
    >>>     with check_error(expected):
    >>>         assert square(input) == expected
    """
    try:
        yield
    except AssertionError:  # the test has failed
        raise
    except Exception as err:  # check if this is expected
        if not isinstance(expected, Exception):
            raise AssertionError("Unexpected error") from err
        if not isinstance(err, expected.__class__):
            raise AssertionError(
                f"Expecting an error, but not the right class: "
                f"{err.__class__} instead of {expected.__class__}")
        if str(err) != str(expected):
            raise AssertionError(
                f"Expecting an error of class {expected.__class__}, "
                f"but the message doesn't match: got \"{err}\" "
                f"instead of \"{expected}\"")
