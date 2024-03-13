from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock, Mock

import pytest

from .context import database as db
from .utils import set_environments, check_error


@pytest.mark.parametrize(
    "MYSQL_DB_ADDRESS,MYSQL_USER,MYSQL_PASSWORD,MYSQL_DATABASE,expected",
    [
        (  # everything alright
                "localhost:3306",
                "user",
                "password",
                "dbname",
                db.DBConnectionData(
                    host="localhost", port=3306,
                    user="user", password="password",
                    dbname="dbname"
                ),
        ),
        (  # wrong port format
                "localhost:unknown",
                "user",
                "password",
                "dbname",
                ValueError("Error: Wrong db port format: unknown!"),
        ),
    ]
)
def test_DBConnectionData_from_environment(
        MYSQL_DB_ADDRESS, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE,
        expected
):
    envs = {
        "MYSQL_DB_ADDRESS": MYSQL_DB_ADDRESS,
        "MYSQL_USER": MYSQL_USER,
        "MYSQL_PASSWORD": MYSQL_PASSWORD,
        "MYSQL_DATABASE": MYSQL_DATABASE
    }
    with set_environments(envs):
        with check_error(expected):
            conn_data = db.DBConnectionData.from_environment()
            assert conn_data == expected, f"Unexpected result={conn_data}"


db_env = {
    "MYSQL_DB_ADDRESS": "localhost:3306",
    "MYSQL_USER": "user",
    "MYSQL_PASSWORD": "password",
    "MYSQL_DATABASE": "dbname",
}


@pytest.mark.asyncio
async def test_Database_create():
    global db_env
    with set_environments(db_env):
        with patch("aiomysql.create_pool", AsyncMock()) as mocked:
            mydb = await db.Database.create()
            assert isinstance(mydb, db.Database)
            kwargs = mocked.call_args.kwargs
            assert kwargs == {
                "host": "localhost",
                "port": 3306,
                "user": "user",
                "password": "password",
                "db": "dbname",
                "autocommit": False,
            }


def create_mock_pool(returned_data: list = None):
    """
    Mock the function aiomysql.create_pool
    Mock the aiomysql.Pool.acquire method as well
    """
    pool = Mock()

    # Save the last cursors for testing purpose
    # (args & kwargs access for example)
    pool.last_cursors = []

    @asynccontextmanager
    async def mocked_pool_acquire():
        nonlocal pool
        conn = Mock()
        conn.commit = AsyncMock()

        @asynccontextmanager
        async def cursor():
            nonlocal pool
            curr = Mock()
            curr.execute = AsyncMock()
            curr.fetchall = AsyncMock(return_value=returned_data or [])
            curr.lastrowid = len(pool.last_cursors)
            pool.last_cursors.append(curr)
            yield curr

        conn.cursor = cursor
        yield conn

    pool.acquire = mocked_pool_acquire
    return pool


@pytest.mark.asyncio
async def test_Database_create_tables():
    global db_env
    with set_environments(db_env):
        # mock the create_pool method
        pool_mocked = create_mock_pool()
        with patch(
                "aiomysql.create_pool",
                AsyncMock(return_value=pool_mocked)
        ):
            mydb = await db.Database.create()
            await mydb.create_tables()

            # the table creation queries
            expected_creation_queries = {
                (
                    "CREATE TABLE IF NOT EXISTS customers"
                    "(id int NOT NULL AUTO_INCREMENT, "
                    "name Varchar(1023), "
                    "PRIMARY KEY (id))"
                ),
                (
                    "CREATE TABLE IF NOT EXISTS accounts"
                    "(id int NOT NULL AUTO_INCREMENT, "
                    "owner_id int, deposit double, "
                    "PRIMARY KEY (id))"
                ),
                (
                    "CREATE TABLE IF NOT EXISTS transfers"
                    "(id int NOT NULL AUTO_INCREMENT, "
                    "from_id int, to_id int, "
                    "`utc_timestamp` int, amount double, "
                    "PRIMARY KEY (id))"
                ),
            }
            queries = {
                m.execute.call_args.args[0]
                for m in pool_mocked.last_cursors
            }
            assert queries == expected_creation_queries


@pytest.mark.parametrize(
    "table,field_values,expected_query",
    [
        (  # missing value for the given field -> failing with ValueError
                db.Tables.accounts,
                ("owner_id",),
                ValueError("Each inserted value should have a field name"),
        ),
        (  # insert integer and double
                db.Tables.accounts,
                ("owner_id", 123, "deposit", 214.56),
                "INSERT INTO accounts (owner_id, deposit) VALUES (123, 214.56)",
        ),
        (  # insert string
                db.Tables.customers,
                ("name", "John Smith",),
                "INSERT INTO customers (name) VALUES ('John Smith')",
        )
    ]
)
@pytest.mark.asyncio
async def test_Database_insert(
        table: db.Tables,
        field_values: tuple[str | int | float],
        expected_query: str
):
    global db_env
    with set_environments(db_env):
        # mock the create_pool method
        pool_mocked = create_mock_pool()
        with patch(
                "aiomysql.create_pool",
                AsyncMock(return_value=pool_mocked)
        ):
            mydb = await db.Database.create()
            with check_error(expected_query):
                lastid = await mydb.insert(table, *field_values)
                assert lastid == 0
                query = pool_mocked.last_cursors[-1].execute.call_args.args[0]
                assert query == expected_query


@pytest.mark.asyncio
async def test_Database_execute():
    global db_env
    with set_environments(db_env):
        # mock the create_pool method
        returned_data = [[123, 234.45]]
        pool_mocked = create_mock_pool(returned_data=returned_data)
        with patch(
                "aiomysql.create_pool",
                AsyncMock(return_value=pool_mocked)
        ):
            mydb = await db.Database.create()
            data = await mydb.execute(
                "SELECT owner_id, deposit FROM accounts WHERE id=1")
            assert data == returned_data
