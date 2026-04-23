# How to contribute

Everyone is free to contribute on this project.

There are two ways to contribute:

- [Submit an issue](https://github.com/Colin-b/pytest_httpx/issues/new/choose).
- [Submit a pull request](https://github.com/Colin-b/pytest_httpx/compare).

## Submitting an issue

Before creating an issue please make sure that it was not already reported.

Title should be a small sentence describing the request.

## Submitting a pull request

### When?

- You fixed an issue.
- You changed something.
- You added a new feature.

### How?

#### Code

1) Create a new branch based on `develop` branch.
2) Fetch all dependencies using [`pip`](https://pip.pypa.io/en/stable/).
    ```shell
    python -m pip install .[testing]
    ```
3) Ensure tests are ok by running them using [`pytest`](https://doc.pytest.org/en/latest/index.html).
    ```shell
    pytest
    ```
4) Install [pre-commit](https://pre-commit.com) hook to ensure new code will follow guidelines.
    ```shell
    python -m pip install pre-commit
    pre-commit install
    ```
5) Add your changes.
6) Add at least one [`pytest`](https://doc.pytest.org/en/latest/index.html) test case.
    * Unless it is an internal refactoring request or a documentation update.
7) Add related [changelog entry](https://keepachangelog.com/en/1.1.0/) in the `Unreleased` section.
    * Unless it is a documentation update.

#### Enter pull request

1) Go to the [*Pull requests* tab](https://github.com/Colin-b/pytest_httpx/pulls) and click on the [*New pull request* button](https://github.com/Colin-b/pytest_httpx/compare).
2) *base* should always be set to `develop` and it should be compared to your branch.
3) Title should be a small sentence describing the request.
4) The comment should contain as much information as possible
    * Actual behavior (before the new code)
    * Expected behavior (with the new code)
    * Steps to reproduce (with and without the new code to see the difference)
