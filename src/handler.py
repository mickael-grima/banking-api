import asyncio

import models
import utils
from database import Database, Tables
from exceptions import NotFoundException

logger = utils.get_logger(__name__)


class Handler(object):
    def __init__(self, db: Database):
        self._db: Database = db

    @classmethod
    async def create(cls):
        db = await Database.create()
        # create tables
        await db.create_tables()
        return cls(db)

    async def create_account(self, customer: str, deposit: float) -> models.Account:
        """
        Create a customer row in the db, if it doesn't exist yet
        Create a new account associated to this customer
        This account has an initial deposit of `deposit` (should be positive)

        :return: The newly created account's id
        """
        if deposit <= 0:
            raise ValueError(
                "[Create Account] Initial deposit is negative or 0, "
                "when it should be positive"
            )

        # create customer if it doesn't exist yet
        owner_id = await self.__get_customer(customer)
        account_id = await self._db.insert(
            Tables.accounts,
            "owner_id",
            owner_id,
            "deposit",
            deposit,
        )

        account = models.Account(id=account_id, owner_id=owner_id, deposit=deposit)
        logger.debug(f"Successfully created new account={account}")
        return account

    async def get_accounts(self, account_id: int | None = None) -> list[models.Account]:
        """
        Return all accounts in DB if `account_id` is None
        Otherwise, return the account corresponding to this id
        If not account is found, a NotFoundException error is raise
        """
        query = f"SELECT id, owner_id, deposit FROM {Tables.accounts.value}"
        if account_id:
            query += f" WHERE id={account_id}"
        rows = await self._db.execute(query)
        if account_id is not None and not rows:
            raise NotFoundException(f"Account with id={account_id} doesn't exist")
        accounts = [models.Account(id=r[0], owner_id=r[1], deposit=r[2]) for r in rows]
        logger.debug(
            f"Successfully found {len(accounts)} accounts from the DB "
            f"matching account_id={account_id}"
        )
        return accounts

    async def transfer(
        self, source_id: int, target_id: int, amount: float
    ) -> models.Transfer:
        """
        Create a new transfer row in the db,
        from `source_id` account to `target_id` account.
        The amount of the transfer is `amount`
        (should always be positive)
        """
        if amount <= 0:
            raise ValueError(
                "[Transfer] transfer amount is negative or 0, "
                "when it should be positive"
            )

        utc_timestamp = utils.get_utc_timestamp()
        transfer_id = await self._db.insert(
            Tables.transfers,
            "from_id",
            source_id,
            "to_id",
            target_id,
            "amount",
            amount,
            "`utc_timestamp`",
            utc_timestamp,
        )

        transfer = models.Transfer(
            id=transfer_id,
            utc_timestamp=utc_timestamp,
            from_id=source_id,
            to_id=target_id,
            amount=amount,
        )
        logger.debug(f"Successfully made a new transfer={transfer}")
        return transfer

    async def get_balances(self, account_id: int) -> models.Balances:
        """
        Find in the db all transfers from or to the given account's id
        If the account doesn't exist, NotFoundException is raised

        :return: the found balances
        """
        # Get account initial deposit
        query = f"SELECT deposit FROM {Tables.accounts.value} " f"WHERE id={account_id}"
        data = await self._db.execute(query)
        if not data:  # account does not exist
            raise NotFoundException(f"Account with id={account_id} doesn't exist")
        deposit = data[0][0]

        # fetch the credits and debits from the DB
        credit_rows, debit_rows = await asyncio.gather(
            self._db.execute(
                f"SELECT amount FROM {Tables.transfers.value} "
                f"WHERE to_id={account_id}"
            ),
            self._db.execute(
                f"SELECT amount FROM {Tables.transfers.value} "
                f"WHERE from_id={account_id}"
            ),
        )

        # get the amount only and compute the sum
        credits = sum([r[0] for r in credit_rows])
        debits = sum([r[0] for r in debit_rows])
        balances = models.Balances(
            account_id=account_id,
            deposit=deposit,
            credits=credits,
            debits=debits,
            balance=deposit + credits - debits,
        )
        logger.debug(
            f"Successfully got balances={balances} " f"from account_id={account_id}"
        )
        return balances

    async def get_transfer_history(
        self, account_id: int, type_: models.TransferType = models.TransferType.any
    ) -> list[models.Transfer]:
        """
        Find in the db all transfers from or to the given account's id
        If the account doesn't exist, NotFoundException is raised

        :param account_id: Account's id
        :param type_: 3 possible values: credit, debit or any.
           -> credit: return only transfer to this account id
           -> debit: return only transfer from this account id
           -> any: return all types of transfers

        :return:the sorted list of transfers, sorted by timestamp, ASCENDING.
        """
        # Check account existence
        if not await self.__account_exists(account_id):
            raise NotFoundException(f"Account with id={account_id} doesn't exist")

        credits, debits = [], []
        match type_:
            case models.TransferType.credit:
                credits = await self.__get_credit_transfers(account_id)
            case models.TransferType.debit:
                debits = await self.__get_debit_transfers(account_id)
            case models.TransferType.any:
                credits, debits = await asyncio.gather(
                    self.__get_credit_transfers(account_id),
                    self.__get_debit_transfers(account_id),
                )
        transfers = sorted(credits + debits, key=lambda t: t.utc_timestamp)
        logger.debug(
            f"Successfully fetched {len(transfers)} of type={type_.value} "
            f"corresponding to account_id={account_id}"
        )
        return transfers

    async def __get_customer(self, customer: str) -> int:
        """
        Get customer from the DB with name "customer" and returns its id
        If it doesn't exist, create it first

        :return: The (new) customer's row's id
        """
        query = f"SELECT id FROM {Tables.customers.value} WHERE name='{customer}'"
        res = await self._db.execute(query)
        if res:  # the customer already exists in the DB: return its id
            return res[0][0]

        # Create the customer
        return await self._db.insert(Tables.customers, "name", customer)

    async def __account_exists(self, account_id: int) -> bool:
        """
        Return True if the account's id exist in the DB, False otherwise
        """
        query = f"SELECT * FROM {Tables.accounts.value} WHERE id={account_id}"
        rows = await self._db.execute(query)
        return bool(rows)

    async def __get_credit_transfers(self, account_id: int) -> list[models.Transfer]:
        """
        Get transfer to this account from the DB,
        and format them into Transfer models
        """
        query = (
            f"SELECT id, from_id, `utc_timestamp`, amount FROM {Tables.transfers.value} "
            f"WHERE to_id={account_id}"
        )
        rows = await self._db.execute(query)
        return [
            models.Transfer(
                id=r[0],
                type=models.TransferType.credit,
                from_id=r[1],
                to_id=account_id,
                utc_timestamp=r[2],
                amount=r[3],
            )
            for r in rows
        ]

    async def __get_debit_transfers(self, account_id: int) -> list[models.Transfer]:
        """
        Get transfer from this account from the DB,
        and format them into Transfer models
        """
        query = (
            f"SELECT id, to_id, `utc_timestamp`, amount FROM {Tables.transfers.value} "
            f"WHERE from_id={account_id}"
        )
        rows = await self._db.execute(query)
        return [
            models.Transfer(
                id=r[0],
                type=models.TransferType.debit,
                from_id=account_id,
                to_id=r[1],
                utc_timestamp=r[2],
                amount=r[3],
            )
            for r in rows
        ]
