# About the solution

The banking-api application is built using the [fastapi](https://fastapi.tiangolo.com/)
framework, an easy-to-set-up and fast web framework, using [uvicorn](https://www.uvicorn.org/)
as an ASGI web server at the top.

The API provides a couple of simple banking functionalities:

- creating customers and accounts, with an initial deposit
- getting existing accounts information, useful to use other endpoints
- making a transfer from one account to another
- accessing the transfers history for a given account

The application stores the data into a [MySQL](https://www.mysql.com/) database

## How to use the API?

First, you need to run your application: check the [Deployment](#deploying-locally) section

The first step is to check the API documentation: http://localhost:8080/redoc

Here are the different endpoint provided by the API:

| Method | Endpoint            | params                                       | description                                                                                                                                                                                                                                                                   | example                                                                                                                      |
|--------|---------------------|----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `POST` | `/account`          | `customer`:str; `deposit`:float              | This endpoint creates an account for the provided customer. If this customer doesn't exist, we create it. An initial `deposit` is credited to this new account                                                                                                                | `curl -X POST 'http://localhost:8080/account?customer=John&deposit=10'`                                                      |
| `POST` | `/transfer`         | `source_id`:int; `to_id`:int; `amount`:float | This endpoint makes a transfer of `amount` from acount's id `source_id` to account id `to_id`. This endpoint doesn't check whether any of the accounts exist, since we consider that the accounts can be external                                                             | `curl -X POST 'http://localhost:8080/transfer?source_id=1&target_id=2&amount=10'`                                            |
| `GET`  | `/account`          | `account_id`:int[optional]                   | This endpoint returns the account corresponding to the provided `account_id`. If no account id are passed, then it returns all accounts. If there is no account with the provided `account_id`, then it returns a 404                                                         | `curl 'http://localhost:8080/account?account_id=1'` for 1 account or `curl 'http://localhost:8080/account'` for all accounts |
| `GET`  | `/account/balance`  | `account_id`:int                             | This endpoint returns the account's balances for the corresponding account's id. The balances is the information of all credits, debits and the balance. If the account does not exist, then it returns a 404                                                                 | `curl 'http://localhost:8080/account/balances?account_id=1'`                                                                 |
| `GET`  | `/transfer/history` | `account_id`:int                             | This endpoint returns the full transfer history from or to this account id `account_id`. Hence, we might encounter 2 types of transfer: `credit` if the trasnfer is to this account, `debit` if it is from this account. If the account doesn't exist, then a 404 is returned | `curl 'http://localhost:8080/transfer/history?account_id=1'`                                                                 |                                                                |

## Things of note

1. This application follows the [twelve Factors-App principles](https://12factor.net/)
2. The code follow strong principles: DRY, KISS, YAGNI, SoC.
3. Only the asked features were implemented, and nothing more (KISS/YAGNI principles).
The only necessary data to use the API endpoints are account ids, that's why a `GET /account` 
endpoint has been added, so we have access to the different accounts ids. Many other 
endpoints could be added, such as `/customer` to create or get customers, but this would add
unnecessary complexity not related to the task. This could be implemented in the future if 
needed, of course

## Deploying locally

### Using Docker

This is the preferred solution to deploy the app, since it is the simplest one.
The only requirement is to have both `docker` and `docker-compose` installed.
Check this [page](https://docs.docker.com/engine/install/) for installation

Then, you can start the app by executing the following command:

```shell
docker-compose -p 'bankingapi' up
```

### Directly on your OS

You can also deploy your API on your current OS, which requires more steps:

0. Before running the application, we need to set-up the environment:

```shell
export MYSQL_DB_ADDRESS="localhost:3306"
export MYSQL_USER="user"
export MYSQL_PASSWORD="password"
export MYSQL_DATABASE="banking-api"
```

Installing the python dependencies is also required:

```shell
pip install -r requirements.txt
```

1. Then, since the application rely on a MySQL database, we need to start one:

```shell
docker run \
  --name "mysqldb" \
  -p "3306:3306" \
  -e "MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD" \
  -e "MYSQL_DATABASE=$MYSQL_DATABASE" \
  -e "MYSQL_USER=$MYSQL_USER" \
  -e "MYSQL_PASSWORD=$MYSQL_PASSWORD" \
  -d mysql
```

2. Finally, we can run the application:

```shell
cd src/ && uvicorn server:app --host "0.0.0.0" --port "8080" --log-level "critical" --reload
```

3. Your banking api is now ready to be used. Check if it is running as expected:

```shell
curl -v 'http://localhost:8080/ping'
```

## Testing

### Unittests

The unittests are implemented under `tests/unittests/`.

#### Best practices

- Any unittest aim to test a single functionality: any outside
  component should be mocked. For example, the `Handler` depends on the `Database` class,
  which needs to be mocked.
- Each publicly accessible function needs to be tested.
- Both successful function's output and potential raised errors need to be tested
- We should aim for the best possible test coverage: 100%

#### How to run the tests

We rely on `tox`. To install it:

```shell
pip install tox
```

Once installed, simply run:

```shell
tox
```

#### About the coverage

As mentioned above, we should aim for the best possible coverage: 100%. However,
there are cases where this coverage is hard to obtain, and would require too much
effort. It is then accepted to lower the targeted coverage, but this should be
mentioned and discussed with the team.

### Integration tests

The integration tests are implemented under `tests/integration_tests/`.

#### Prerequisites

Those tests suppose that an healthy app is already up and running. Refer to
the section [Deployment](#deploying-locally).

#### Running the tests

1. go to the `integration_tests` directory:

```shell
cd tests/integration_tests/
```

2. run the tests:

```shell
bash run.sh
```

You should see a succession of green printed lines. Each line represents
a successful test.

If a red line is printed out, it means the test failed for this specific testcase.
In this case, check your application logs to understand what is going wrong.

#### Adding a test-case

The test cases are hardcoded inside the script `src/main.py`, under the
`test_cases` global variables.

To add a test case, you only need to add a new entry in the `test_cases` list.
This entry should be a `tester.TestCase` object, as the following example:

```python
from tester import TestCase, Request
from api_client import APIResponse

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
)
```

it defines:

- a `name`, describing what the test is about. This name is printed in the console
  and should help finding the successful/failing test
- a `request`, used to call the API
- a `response`, defining an expecting status code and json body

> **Note**: the list of `test_cases` has a given order which is important.
> For example, accounts creations should happen before getting the balances

## About logging

Following the [twelve Factors-App principles](https://12factor.net/), the logs are all streamed to the
console. It is then up to the infrastructure to decide what to do with those logs.

Doing so, we comply to the SoC principle, where each service has a given task.
And it is not this application's task to manage the logs

Also, the logs management become easier:

- changing the logs monitoring system doesn't affect the app, and vice-versa
- we don't risk storing logs on some unknown place, resulting to higher cost,
  or to OOM errors (leading most of the time to application failure).

## The CI/CD

The CI/CD is handled by github action's workflows define in `.github/workflows/`.

There are a couple of variables that are still unset, and that we should set
before making it run:

- *the targeted branch*: it should be `master` (we could also include branches
  like `releases/v**` for staging and prod releases). To trigger the workflow,
  it was replaced by another branch that shouldn't exist
- *the AWS account id*: as explained below, the CD push the newly created docker
  image to an AWS ECR registry, and requires an account to do so.

> **Note**: for obvious reasons, the workflows weren't tested, and might fail.
> This is only a first version that might need refinement

### Continuous Integration (CI)

The CI is defined in `.github/workflows/ci.yaml`. It has 3 main jobs:

- **unittests**: run the unittests defined in `tests/unittests`
- **integration tests**: run the integration tests defined in
  `tests/integration_tests`
- **vulnerabilities**: it build the docker image and check its vulnerabilities
  using [trivy](https://trivy.dev/)

### Continuous Deployment (CD)

The CD is defined in `.github/workflows/push-to-ecr.yaml`

We suppose that this application will be part of a greater backend service,
and will be deployed as a docker container using the AWS services (ECS, EKS, etc ...)

Considering that, the CD does the following:

- build the docker image
- tag it using the latest git commit id
- push it to AWS ECR

This image can then be consumed by AWS services from ECR

## Ideas of Improvement

### Credits & Debits pre-computation

For simplicity sake (KISS principle), and because this app remains small with only
few data in the DB, we compute credits and debits for a given account on live request,
by getting all transfer's amount from the DB.

When the app grows, the amount of stored transfer will grow as well, and this solution
might become slower and slower. A solution would be to pre-compute and save credits
and debits everytime a transfer is made. Those credits and debits could be a new column
in the `accounts` table. This solution would increase the performance of the
`/account/balances` endpoint.

### Instrumentation

Using either [opentelemetry](https://opentelemetry.io/docs/languages/python/getting-started/)
or [Datadog](https://docs.datadoghq.com/fr/integrations/python/), we can instrument the code
and get deeper insights while monitoring & debugging the application.

This would take more effort and time, that's why I haven't done it here.
