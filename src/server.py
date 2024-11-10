from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.responses import Response

import middleware
import models
import utils
from handler import Handler

logger = utils.get_logger(__name__)

description = """This API provides primary functions to:
- create accounts and get information from it, such as balances
- make transfers from one account to another
- get transfers history from any account
"""

tags_metadata = [
    {
        "name": "accounts",
        "description": "Operations with accounts",
    },
    {
        "name": "transfers",
        "description": "Operations with transfers",
    },
]

# The data handler, in charge of the internal logic
# To initialize it, we need to call `Handler.create`,
# which is possible only inside an async function
handler: Handler | None = None


@asynccontextmanager
async def lifespan(_):
    """Before the application starts, we need to initialize handler"""
    global handler
    # Initialize the handler, and its underlying DB client
    try:
        handler = await Handler.create()
    except:
        logger.critical("Unexpected failure while creating the handler")
        raise
    yield
    # delete the handler object while the event loop is still not closed
    del handler


app = FastAPI(
    title="Simple Banking API",
    description=description,
    summary="API to handle accounts",
    version="0.0.1",
    lifespan=lifespan,
)

# add middleware to log request events & errors
app.add_middleware(middleware.LoggerMiddleware)


@app.get("/ping", include_in_schema=False)
def ping():
    return Response("OK!")


@app.post(
    "/account",
    tags=["accounts"],
    status_code=status.HTTP_201_CREATED,
    response_model=models.Account,
    response_model_exclude_none=True,
)
async def create_account(customer: str, deposit: float):
    return await handler.create_account(customer, deposit)


@app.get(
    "/account",
    tags=["accounts"],
    response_model=list[models.Account],
)
async def get_accounts(account_id: int | None = None):
    return await handler.get_accounts(account_id=account_id)


@app.get(
    "/account/balances",
    tags=["accounts"],
    response_model=models.Balances,
)
async def get_balances(account_id: int):
    return await handler.get_balances(account_id)


@app.post(
    "/transfer",
    tags=["transfers"],
    status_code=status.HTTP_201_CREATED,
    response_model=models.Transfer,
    response_model_exclude_defaults=True,
)
async def accounts_transfer(
    source_id: int, target_id: int, amount: float
) -> models.Transfer:
    return await handler.transfer(source_id, target_id, amount)


@app.get(
    "/transfer/history",
    tags=["transfers"],
    response_model=list[models.Transfer],
)
async def get_transfer_history(
    account_id: int, transfer_type: models.TransferType = models.TransferType.any
):
    return await handler.get_transfer_history(account_id, type_=transfer_type)
