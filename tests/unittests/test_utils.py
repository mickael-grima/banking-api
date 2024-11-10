import logging
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from .context import utils
from .utils import set_environments


@freeze_time("2024-03-11T06:13:00Z")
def test_get_utc_timestamp():
    expected = 1710137580
    res = utils.get_utc_timestamp()
    assert res == expected, f"Expecting {expected}, got {res} instead"


@pytest.mark.parametrize(
    "status_code,expected",
    [
        (200, '"GET http://localhost:8080/ping" 200 OK'),
        (404, '"GET http://localhost:8080/ping" 404 Not Found'),
        (500, '"GET http://localhost:8080/ping" 500 Internal Server Error'),
    ],
)
def test_server_log_message(status_code: int, expected: str):
    req = Mock()
    req.method = "GET"
    req.url = "http://localhost:8080/ping"
    mess = utils.server_log_message(req, status_code)
    assert mess == expected


@pytest.mark.parametrize(
    "debug,expected_level",
    [
        ("1", logging.DEBUG),
        ("0", logging.INFO),
        ("unknown", logging.INFO),
    ],
)
def test_get_logger(debug: str, expected_level: int):
    with set_environments({"DEBUG": debug}):
        logger: logging.Logger = utils.get_logger(__name__)
        assert logger.level == expected_level
