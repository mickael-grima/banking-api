from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time

from .context import exceptions as exc
from .context import handler as hd
from .context import models
from .utils import check_error


@patch("database.Database.create", AsyncMock())
@pytest.mark.asyncio
async def test_Handler_create():
    handler = await hd.Handler.create()
    assert isinstance(handler, hd.Handler)


@pytest.mark.parametrize(
    "customer,deposit,expected",
    [
        (  # deposit is negative, but should be positive
            "John",
            -123,
            ValueError(
                "[Create Account] Initial deposit is negative or 0, "
                "when it should be positive"
            ),
        ),
        (  # new customer John should be created
            "John",
            234.56,
            models.Account(id=123, owner_id=456, deposit=234.56),
        ),
        (  # customer Kevin should already exist
            "Kevin",
            234.56,
            models.Account(id=789, owner_id=456, deposit=234.56),
        ),
    ],
)
@pytest.mark.asyncio
async def test_Handler_create_account(customer, deposit, expected):
    with patch("database.Database.create", AsyncMock()):
        handler = await hd.Handler.create()
        match customer:
            case "John":  # new customer is created
                handler._db.execute = AsyncMock(return_value=[])
                handler._db.insert = AsyncMock(side_effect=[456, 123])
            case _:  # customer already exists
                handler._db.execute = AsyncMock(return_value=[[456]])
                handler._db.insert = AsyncMock(side_effect=[789])
        with check_error(expected):
            account = await handler.create_account(customer, deposit)
            assert account == expected


@pytest.mark.parametrize(
    "account_id,expected",
    [
        (
            0,
            exc.NotFoundException("Account with id=0 doesn't exist"),
        ),
        (123, [models.Account(id=123, owner_id=456, deposit=234.56)]),
        (
            None,
            [
                models.Account(id=123, owner_id=456, deposit=234.56),
                models.Account(id=111, owner_id=789, deposit=100.0),
            ],
        ),
    ],
)
@pytest.mark.asyncio
async def test_Handler_get_accounts(
    account_id: int, expected: Exception | list[models.Account]
):
    with patch("database.Database.create", AsyncMock()):
        handler = await hd.Handler.create()
        match account_id:
            case 0:
                handler._db.execute = AsyncMock(return_value=[])
            case 123:
                handler._db.execute = AsyncMock(
                    return_value=[
                        [123, 456, 234.56],
                    ]
                )
            case None:
                handler._db.execute = AsyncMock(
                    return_value=[
                        [123, 456, 234.56],
                        [111, 789, 100.0],
                    ]
                )
        with check_error(expected):
            accounts = await handler.get_accounts(account_id=account_id)
            assert accounts == expected


@freeze_time("2024-03-11T06:13:00Z")
@pytest.mark.parametrize(
    "amount,expected",
    [
        (  # amount is negative, but should be positive
            -123,
            ValueError(
                "[Transfer] transfer amount is negative or 0, "
                "when it should be positive"
            ),
        ),
        (  # amount is, as expected, positive
            234.56,
            models.Transfer(
                id=123,
                from_id=111,
                to_id=222,
                utc_timestamp=1710137580,
                amount=234.56,
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_Handler_transfer(amount, expected):
    with patch("database.Database.create", AsyncMock()):
        handler = await hd.Handler.create()
        handler._db.insert = AsyncMock(return_value=123)
        with check_error(expected):
            transfer = await handler.transfer(111, 222, amount)
            assert transfer == expected


@pytest.mark.parametrize(
    "account_id,expected",
    [
        (  # account does not exist and error is raised
            0,
            exc.NotFoundException("Account with id=0 doesn't exist"),
        ),
        (  # everything works as expected
            123,
            models.Balances(
                account_id=123,
                deposit=10,
                credits=15,
                debits=13,
                balance=12,
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_Handler_get_balances(account_id: int, expected: models.Balances):
    with patch("database.Database.create", AsyncMock()):
        handler = await hd.Handler.create()
        match account_id:
            case 0:  # This account doesn't exist in the DB
                handler._db.execute = AsyncMock(return_value=[])
            case _:  # all other accounts exist
                handler._db.execute = AsyncMock(
                    side_effect=[
                        [[10]],  # initial account's deposit
                        [[3], [7], [5]],  # credits rows (amount only)
                        [[6], [7]],  # debits rows (amount only)
                    ]
                )
        with check_error(expected):
            balances = await handler.get_balances(account_id)
            assert balances == expected


@pytest.mark.parametrize(
    "account_id,transfer_type,expected",
    [
        (  # account does not exist and error is raised
            0,
            models.TransferType.any,
            exc.NotFoundException("Account with id=0 doesn't exist"),
        ),
        (  # any type of transfers
            123,
            models.TransferType.any,
            [
                models.Transfer(
                    id=1,
                    utc_timestamp=1710137580,
                    type=models.TransferType.credit,
                    from_id=456,
                    to_id=123,
                    amount=100,
                ),
                models.Transfer(
                    id=2,
                    utc_timestamp=1710137590,
                    type=models.TransferType.debit,
                    from_id=123,
                    to_id=789,
                    amount=200,
                ),
                models.Transfer(
                    id=3,
                    utc_timestamp=1710137600,
                    type=models.TransferType.credit,
                    from_id=789,
                    to_id=123,
                    amount=25,
                ),
            ],
        ),
        (  # credits transfers
            123,
            models.TransferType.credit,
            [
                models.Transfer(
                    id=1,
                    utc_timestamp=1710137580,
                    type=models.TransferType.credit,
                    from_id=456,
                    to_id=123,
                    amount=100,
                ),
                models.Transfer(
                    id=3,
                    utc_timestamp=1710137600,
                    type=models.TransferType.credit,
                    from_id=789,
                    to_id=123,
                    amount=25,
                ),
            ],
        ),
        (  # debits transfers
            123,
            models.TransferType.debit,
            [
                models.Transfer(
                    id=2,
                    utc_timestamp=1710137590,
                    type=models.TransferType.debit,
                    from_id=123,
                    to_id=789,
                    amount=200,
                ),
            ],
        ),
    ],
)
@pytest.mark.asyncio
async def test_Handler_get_transfer_history(
    account_id: int, transfer_type: models.TransferType, expected: list[models.Transfer]
):
    with patch("database.Database.create", AsyncMock()):
        handler = await hd.Handler.create()
        match (account_id, transfer_type):
            case (0, _):  # This account doesn't exist in the DB
                handler._db.execute = AsyncMock(return_value=[])
            case (_, models.TransferType.any):
                handler._db.execute = AsyncMock(
                    side_effect=[
                        [[account_id, "Kevin"]],
                        [[1, 456, 1710137580, 100.0], [3, 789, 1710137600, 25.0]],
                        [[2, 789, 1710137590, 200.0]],
                    ]
                )
            case (_, models.TransferType.credit):
                handler._db.execute = AsyncMock(
                    side_effect=[
                        [[account_id, "Kevin"]],
                        [[1, 456, 1710137580, 100.0], [3, 789, 1710137600, 25.0]],
                    ]
                )
            case (_, models.TransferType.debit):
                handler._db.execute = AsyncMock(
                    side_effect=[
                        [[account_id, "Kevin"]],
                        [[2, 789, 1710137590, 200.0]],
                    ]
                )
        with check_error(expected):
            transfers = await handler.get_transfer_history(
                account_id, type_=transfer_type
            )
            assert transfers == expected
