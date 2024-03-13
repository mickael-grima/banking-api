from enum import Enum

import pydantic
from pydantic import Field


class TransferType(Enum):
    credit = "credit"
    debit = "debit"
    any = "any"


class Customer(pydantic.BaseModel):
    id: int = ...
    name: str = Field(..., title="Customer's full name")


class Transfer(pydantic.BaseModel):
    id: int = ...
    type: TransferType = Field(
        TransferType.any,
        description=(
            "The type of transfer: debit if the transfer is from this account, "
            "credit if it is to this account")
    )
    utc_timestamp: int = Field(
        ...,
        description="UTC timestamp when the transfer happened"
    )
    from_id: int = Field(
        ...,
        description="Transfer from this account's id"
    )
    to_id: int = Field(
        ...,
        description="Transfer to this account's id"
    )
    amount: float = Field(
        ...,
        description="Transfer's amount. Always positive"
    )


class Balances(pydantic.BaseModel):
    account_id: int = Field(
        ...,
        description="Account to which the credits and debits belong"
    )
    deposit: float = Field(
        ...,
        description="Initial deposit when the account is created"
    )
    credits: float = Field(
        0,
        description="Sum of all credits made to this account, since its creation"
    )
    debits: float = Field(
        0,
        description="Sum of all debits made to this account, since its creation"
    )
    balance: float = Field(
        0,
        description="Difference between credits and debits"
    )


class Account(pydantic.BaseModel):
    id: int = ...
    owner_id: int = Field(..., description="The account's owner's id")
    deposit: float = Field(..., description="Initial deposit when the account is created")
