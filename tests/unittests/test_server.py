from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from .context import exceptions as exc
from .context import models, server

# By default the TestClient will raise any exceptions that occur in the
# application.
# Occasionally you might want to test the content of 500 error responses,
# rather than allowing client to raise the server exception.
# docs: https://www.starlette.io/testclient/
client = TestClient(server.app, raise_server_exceptions=False)

test_cases = [
    (  # successful account creation
        "POST",
        "/account",
        {"customer": "John", "deposit": 234.56},
        None,
        {"id": 123, "owner_id": 456, "deposit": 234.56},
        201,
    ),
    (  # account creation - unexpected error raised
        "POST",
        "/account",
        {"customer": "John", "deposit": -1},
        ValueError("deposit is negative!"),
        {"error": "INTERNAL_ERROR", "message": "Oops! Something went wrong!"},
        500,
    ),
    (  # get account with given id
        "GET",
        "/account",
        {"account_id": 123},
        None,
        [{"id": 123, "owner_id": 456, "deposit": 234.56}],
        200,
    ),
    (  # get all accounts
        "GET",
        "/account",
        {},
        None,
        [
            {"id": 123, "owner_id": 456, "deposit": 234.56},
            {"id": 111, "owner_id": 456, "deposit": 100.0},
        ],
        200,
    ),
    (  # get accounts with id - unexpected raised error
        "GET",
        "/account",
        {"account_id": 123},
        exc.NotFoundException("account does not exist"),
        {"error": "NOT_FOUND", "message": "account does not exist"},
        404,
    ),
    (  # get all accounts, no results
        "GET",
        "/account",
        {},
        None,
        [],
        200,
    ),
    (  # get account's balances
        "GET",
        "/account/balances",
        {"account_id": 123},
        None,
        {
            "account_id": 123,
            "deposit": 10.0,
            "credits": 10.0,
            "debits": 13.56,
            "balance": 6.44,
        },
        200,
    ),
    (  # get account's balances - account does not exist
        "GET",
        "/account/balances",
        {"account_id": 123},
        exc.NotFoundException("account does not exist"),
        {"error": "NOT_FOUND", "message": "account does not exist"},
        404,
    ),
    (  # get account's balances - unexpected raised error
        "GET",
        "/account/balances",
        {"account_id": 123},
        ValueError("whatever error"),
        {"error": "INTERNAL_ERROR", "message": "Oops! Something went wrong!"},
        500,
    ),
    (  # make transfer
        "POST",
        "/transfer",
        {"source_id": 1, "target_id": 2, "amount": 234.56},
        None,
        {
            "id": 1,
            "utc_timestamp": 1710137580,
            "from_id": 1,
            "to_id": 2,
            "amount": 234.56,
        },
        201,
    ),
    (  # make transfer with negative amount
        "POST",
        "/transfer",
        {"source_id": 1, "target_id": 2, "amount": -1},
        ValueError("amount is negative!"),
        {"error": "INTERNAL_ERROR", "message": "Oops! Something went wrong!"},
        500,
    ),
    (  # get transfer history
        "GET",
        "/transfer/history",
        {"account_id": 123},
        None,
        [
            {
                "id": 1,
                "type": "credit",
                "utc_timestamp": 1710137580,
                "from_id": 1,
                "to_id": 123,
                "amount": 100,
            },
            {
                "id": 2,
                "type": "debit",
                "utc_timestamp": 1710137590,
                "from_id": 123,
                "to_id": 2,
                "amount": 25,
            },
        ],
        200,
    ),
    (  # get transfer history for non-existing account
        "GET",
        "/transfer/history",
        {"account_id": 123},
        exc.NotFoundException("account does not exist"),
        {"error": "NOT_FOUND", "message": "account does not exist"},
        404,
    ),
    (  # make transfer history - unexpected raised error
        "GET",
        "/transfer/history",
        {"account_id": 123},
        ValueError("whatever error"),
        {"error": "INTERNAL_ERROR", "message": "Oops! Something went wrong!"},
        500,
    ),
]


def mock_handler(
    method: str, path: str, err: Exception | None, data: dict | list[dict]
) -> Mock:
    """
    Depending on the method & path, mock the handler accordingly
    if `err` is not None, the handler will raise this error
    otherwise it will return modelled data
    """
    handler = Mock()
    if err is not None:
        handler.create_account = AsyncMock(side_effect=err)
        handler.get_accounts = AsyncMock(side_effect=err)
        handler.get_balances = AsyncMock(side_effect=err)
        handler.transfer = AsyncMock(side_effect=err)
        handler.get_transfer_history = AsyncMock(side_effect=err)
    else:
        match path:
            case "/account":
                if method.upper() == "POST":
                    res = AsyncMock(return_value=models.Account(**data))
                    handler.create_account = res
                if method.upper() == "GET":
                    res = AsyncMock(return_value=[models.Account(**d) for d in data])
                    handler.get_accounts = res
            case "/account/balances":
                res = AsyncMock(return_value=models.Balances(**data))
                handler.get_balances = res
            case "/transfer":
                res = AsyncMock(return_value=models.Transfer(**data))
                handler.transfer = res
            case "/transfer/history":
                res = AsyncMock(return_value=[models.Transfer(**d) for d in data])
                handler.get_transfer_history = res
    return handler


@pytest.mark.parametrize(
    "method,path,params,handler_error,response_body,response_status_code", test_cases
)
def test_routes(
    method: str,
    path: str,
    params: dict[str, str],
    handler_error: Exception | None,
    response_body: dict | list[dict],
    response_status_code: int,
):
    # mock handler
    server.handler = mock_handler(method, path, handler_error, response_body)

    # call API
    match method.upper():
        case "POST":
            res = client.post(path, params=params)
        case _:  # GET case
            res = client.get(path, params=params)

    # check response
    assert res.status_code == response_status_code
    assert res.json() == response_body
    server.handler = None


def test_ping():
    res = client.get("/ping")
    assert res.status_code == 200
    assert res.text == "OK!"


@pytest.mark.asyncio
async def test_lifespan():
    # successful creation
    with patch("handler.Handler.create", AsyncMock()):
        async with server.lifespan(server.app):
            assert server.handler is not None
        server.handler = None

    # error during creation
    with patch("handler.Handler.create", AsyncMock(side_effect=ValueError("error"))):
        with pytest.raises(ValueError) as exc_info:
            async with server.lifespan(server.app):
                pass
        assert exc_info.type is ValueError
