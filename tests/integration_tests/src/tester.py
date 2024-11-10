import dataclasses
from typing import Awaitable, Callable

from api_client import APIClient, APIResponse
from termcolor import colored


@dataclasses.dataclass
class Request:
    method: str
    path: str
    params: dict[str, str] | None = None


@dataclasses.dataclass
class TestCase:
    name: str
    request: Request  # API request
    response: APIResponse  # expected API response

    def check_response(self, resp: APIResponse):
        """
        Check if the self.response corresponds to resp
        raise errors accordingly
        """
        if resp.status_code != self.response.status_code:
            raise ValueError(
                f"Wrong status-code={resp.status_code} while "
                f"{self.response.status_code} was expected instead"
            )
        # remove timestamp from the response (too volatile)
        resp.remove_fields("utc_timestamp")
        if resp.json_body != self.response.json_body:
            raise ValueError(f'Wrong response body="{resp.json_body}"')

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}< {self.name} -- "
            f"{self.request.method} {self.request.path} >"
        )


class Tester:
    """
    This class implements functionalities to test the API calls
    responses
    """

    def __init__(self, api_client: APIClient, test_cases: list[TestCase]):
        self._api_client = api_client
        self._test_cases = test_cases

    async def run(self):
        """
        run all tests and stop to the first one failing
        Print a nice log to the console if needed
        """
        print(f"Starting {len(self._test_cases)} tests ...")
        success = True
        for testcase in self._test_cases:
            try:
                await self.__test(testcase)
                print_success(testcase)
            except Exception as exc:
                print_failure(testcase, exc)
                success = False
                break
        result = colored("SUCCESS", "green") if success else colored("FAILURE", "red")
        print(f"Finished testing! Result={result}")

    async def __test(self, testcase: TestCase):
        """
        Call the API with testcase.request and check the API response
        """
        caller: Callable[[str, dict | None], Awaitable[APIResponse]]
        match testcase.request.method.upper():
            case "GET":
                caller = self._api_client.get
            case "POST":
                caller = self._api_client.post
            case _:
                raise ValueError(
                    f"method={testcase.request.method.upper()} not supported"
                )

        resp = await caller(testcase.request.path, params=testcase.request.params)
        testcase.check_response(resp)


def print_failure(testcase: TestCase, err: Exception):
    print(colored(f"FAILURE {testcase}: {err}", "red"))


def print_success(testcase: TestCase):
    print(colored(f"SUCCESS {testcase}", "green"))
