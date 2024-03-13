import asyncio
import dataclasses
import os
from enum import Enum

import aiomysql

import utils

logger = utils.get_logger(__name__)


class Tables(Enum):
    transfers = "transfers"
    customers = "customers"
    accounts = "accounts"


@dataclasses.dataclass
class DBConnectionData:
    host: str
    port: int
    user: str
    password: str
    dbname: str

    @classmethod
    def from_environment(cls) -> "DBConnectionData":
        """
        Read Database  address, credentials & db name from environments
        """
        # load from environments
        host, port = os.getenv("MYSQL_DB_ADDRESS").split(":")
        user = os.getenv("MYSQL_USER")
        password = os.getenv("MYSQL_PASSWORD")
        dbname = os.getenv("MYSQL_DATABASE")

        # transform port to an int
        # it should raise if the port has not the right format
        try:
            port = int(port)
        except ValueError as e:
            raise ValueError(f"Error: Wrong db port format: {port}!") from e

        return cls(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )


class Database(object):
    def __init__(self):
        self._pool: aiomysql.Pool | None = None

    @classmethod
    async def create(cls) -> "Database":
        """
        __init__ can't be async. This function simulate an async __init__
        It should be called to initialize a Database

        >>> db = await Database.create()
        """
        self = cls()

        # Read Database  address, credentials & db name from environments
        data = DBConnectionData.from_environment()

        # The password is not logged (even debug) for security reasons
        logger.info(
            f"Connecting to Database=(address={data.host}:{data.port} "
            f"creds={data.user}:xxx dbname={data.dbname} )")

        # create the pool
        self._pool = await aiomysql.create_pool(
            host=data.host, port=data.port,
            user=data.user, password=data.password,
            db=data.dbname, autocommit=False)
        return self

    def __del__(self):
        if self._pool:
            self._pool.close()

    async def __create_table(self, table: Tables, *columns: str):
        """
        Create `table` with field given columns
        The table has an auto-incremented primary key id created

        :param table: the table to create
        :param columns: a collection of column-name, column-type

        >> self.__create_table(
        >>     Tables.transfer,
        >>     "from_id", "int",
        >>     "to_id", "int",
        >>     "utc_timestamp", "int")

        This will create a table with the SQL query:
          CREATE TABLE transfers(id int NOT NULL AUTO_INCREMENT, from_id int, to_id int, utc_timestamp int, PRIMARY_KEY (id))
        """
        fields = ", ".join([
            f"{columns[2 * i]} {columns[2 * i + 1]}"
            for i in range(int(len(columns) / 2))
        ])
        query = (
            f"CREATE TABLE IF NOT EXISTS {table.value}"
            f"(id int NOT NULL AUTO_INCREMENT, {fields}, PRIMARY KEY (id))"
        )
        logger.info(f"[MySQL] Create new table from query=\"{query}\"")
        async with self._pool.acquire() as conn:
            async with conn.cursor() as curr:
                await curr.execute(query)
                await conn.commit()

    async def create_tables(self):
        """
        Create the 3 tables: transfers, accounts, customers
        The creation happens only if they don't exist
        """
        await asyncio.wait([
            self.__create_table(
                Tables.transfers,
                "from_id", "int",
                "to_id", "int",
                "`utc_timestamp`", "int",
                "amount", "double",
            ),
            self.__create_table(
                Tables.accounts,
                "owner_id", "int",
                "deposit", "double",
            ),
            self.__create_table(
                Tables.customers,
                "name", "Varchar(1023)",
            ),
        ])

    async def insert(self, table: Tables, *field_values: str | int | float) -> int:
        """
        Insert a new row into table with the given fields & values

        :param table: Table where to insert the new row
        :param field_values: Fields & values to insert.
        :return: The newly created row's id

        **Example**
        >> self.insert(Tables.customers, "name", "John Smith")
        This command insert a new row with name John Smith, and return its
        auto-generated id
        """
        if len(field_values) % 2 != 0:
            raise ValueError("Each inserted value should have a field name")
        async with self._pool.acquire() as conn:
            async with conn.cursor() as curr:
                # collect field & values from field_values
                fields = ", ".join(field_values[::2])
                values = ", ".join(
                    [f"{f}" if not isinstance(f, str) else f"'{f}'" for f in field_values[1::2]])

                # request the DB
                query = f"INSERT INTO {table.value} ({fields}) VALUES ({values})"
                logger.debug(f"MySQL: Executing query={query}")
                await curr.execute(query)
                await conn.commit()
                logger.debug(
                    f"Successfully inserted new row fields=({fields}) values=({values}) "
                    f"into table={table.value}")
                return curr.lastrowid

    async def execute(self, query: str):
        """
        Execute the given SQL query and return all the found results
        To get a unique row, one can simply call this method and get the
        first element
        """
        logger.debug(f"MySQL: Executing query={query}")
        async with self._pool.acquire() as conn:
            async with conn.cursor() as curr:
                await curr.execute(query)
                await conn.commit()
                return await curr.fetchall()
