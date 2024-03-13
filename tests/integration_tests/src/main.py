import asyncio
import os

from dotenv import load_dotenv

from tester import Tester, TestCase, Request
from api_client import APIClient, APIResponse

curr_dir = os.path.dirname(os.path.realpath(__file__))
env_filename = os.path.join(curr_dir, "..", "test.env")

test_cases: list[TestCase] = [
    # Create a couple of accounts first
    TestCase(
        name="Create-John-first-account",
        request=Request(
            method="POST",
            path="/account",
            params={"customer": "John", "deposit": "100."}
        ),
        response=APIResponse(
            status_code=201,
            json_body={"id": 1, "owner_id": 1, "deposit": 100.}
        )
    ),
    TestCase(
        name="Create-Kevin-first-account",
        request=Request(
            method="POST",
            path="/account",
            params={"customer": "Kevin", "deposit": "200."}
        ),
        response=APIResponse(
            status_code=201,
            json_body={"id": 2, "owner_id": 2, "deposit": 200.}
        )
    ),
    TestCase(
        name="Create-John-second-account",
        request=Request(
            method="POST",
            path="/account",
            params={"customer": "John", "deposit": "50."}
        ),
        response=APIResponse(
            status_code=201,
            json_body={"id": 3, "owner_id": 1, "deposit": 50.}
        )
    ),

    # Get all accounts
    TestCase(
        name="Get-all-accounts",
        request=Request(
            method="GET",
            path="/account",
        ),
        response=APIResponse(
            status_code=200,
            json_body=[
                {"id": 1, "owner_id": 1, "deposit": 100.},
                {"id": 2, "owner_id": 2, "deposit": 200.},
                {"id": 3, "owner_id": 1, "deposit": 50.}
            ]
        )
    ),

    # Get a non-existing account
    TestCase(
        name="Get-non-existing-account",
        request=Request(
            method="GET",
            path="/account",
            params={"account_id": "12345"}
        ),
        response=APIResponse(
            status_code=404,
            json_body={"error": "NOT_FOUND", "message": "Account with id=12345 doesn't exist"}
        )
    ),

    # Get existing account
    TestCase(
        name="Get-existing-account",
        request=Request(
            method="GET",
            path="/account",
            params={"account_id": "1"}
        ),
        response=APIResponse(
            status_code=200,
            json_body=[{"id": 1, "owner_id": 1, "deposit": 100.}],
        )
    ),

    # Make a couple of transfers
    TestCase(
        name="transfer-account-1-to-2",
        request=Request(
            method="POST",
            path="/transfer",
            params={"source_id": "1", "target_id": "2", "amount": "25."},
        ),
        response=APIResponse(
            status_code=201,
            json_body={"id": 1, "from_id": 1, "to_id": 2, "amount": 25.}
        )
    ),
    TestCase(
        name="transfer-account-1-to-3",
        request=Request(
            method="POST",
            path="/transfer",
            params={"source_id": "1", "target_id": "3", "amount": "30."},
        ),
        response=APIResponse(
            status_code=201,
            json_body={"id": 2, "from_id": 1, "to_id": 3, "amount": 30.}
        )
    ),
    TestCase(
        name="transfer-account-2-to-1",
        request=Request(
            method="POST",
            path="/transfer",
            params={"source_id": "2", "target_id": "1", "amount": "50."},
        ),
        response=APIResponse(
            status_code=201,
            json_body={"id": 3, "from_id": 2, "to_id": 1, "amount": 50.}
        )
    ),

    # Check balances
    TestCase(
        name="account-1-balances",
        request=Request(
            method="GET",
            path="/account/balances",
            params={"account_id": "1"},
        ),
        response=APIResponse(
            status_code=200,
            json_body={
                "account_id": 1,
                "deposit": 100.,
                "credits": 50.,
                "debits": 55.,
                "balance": 95.
            },
        )
    ),
    TestCase(
        name="account-2-balances",
        request=Request(
            method="GET",
            path="/account/balances",
            params={"account_id": "2"},
        ),
        response=APIResponse(
            status_code=200,
            json_body={
                "account_id": 2,
                "deposit": 200.,
                "credits": 25.,
                "debits": 50.,
                "balance": 175.
            },
        )
    ),
    TestCase(
        name="account-3-balances",
        request=Request(
            method="GET",
            path="/account/balances",
            params={"account_id": "3"},
        ),
        response=APIResponse(
            status_code=200,
            json_body={
                "account_id": 3,
                "deposit": 50.,
                "credits": 30.,
                "debits": 0.,
                "balance": 80.
            },
        )
    ),
    TestCase(
        name="non-existing-account-balances",
        request=Request(
            method="GET",
            path="/account/balances",
            params={"account_id": "12345"},
        ),
        response=APIResponse(
            status_code=404,
            json_body={"error": "NOT_FOUND", "message": "Account with id=12345 doesn't exist"},
        )
    ),

    # Get transfer history
    TestCase(
        name="account-1-transfer-history",
        request=Request(
            method="GET",
            path="/transfer/history",
            params={"account_id": "1"},
        ),
        response=APIResponse(
            status_code=200,
            # the order is not ensured since the API calls are made within a second
            json_body=[
                {"id": 1, "type": "debit", "from_id": 1, "to_id": 2, "amount": 25.},
                {"id": 2, "type": "debit", "from_id": 1, "to_id": 3, "amount": 30.},
                {"id": 3, "type": "credit", "from_id": 2, "to_id": 1, "amount": 50.},
            ],
        )
    ),
    TestCase(
        name="account-2-transfer-history",
        request=Request(
            method="GET",
            path="/transfer/history",
            params={"account_id": "2"},
        ),
        response=APIResponse(
            status_code=200,
            json_body=[
                {"id": 1, "type": "credit", "from_id": 1, "to_id": 2, "amount": 25.},
                {"id": 3, "type": "debit", "from_id": 2, "to_id": 1, "amount": 50.}
            ],
        )
    ),
    TestCase(
        name="account-3-transfer-history",
        request=Request(
            method="GET",
            path="/transfer/history",
            params={"account_id": "3"},
        ),
        response=APIResponse(
            status_code=200,
            json_body=[
                {"id": 2, "type": "credit", "from_id": 1, "to_id": 3, "amount": 30.},
            ],
        )
    ),
    TestCase(
        name="non-existing-account-transfer-history",
        request=Request(
            method="GET",
            path="/transfer/history",
            params={"account_id": "12345"},
        ),
        response=APIResponse(
            status_code=404,
            json_body={"error": "NOT_FOUND", "message": "Account with id=12345 doesn't exist"},
        )
    ),

]


async def main():
    load_dotenv(env_filename)
    host = os.getenv("API_HOST")
    api_client = APIClient(host)
    tester = Tester(api_client, test_cases)
    await tester.run()


if __name__ == '__main__':
    asyncio.run(main())
