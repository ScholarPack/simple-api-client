![Build Status](https://github.com/ScholarPack/simple-api-client/workflows/Validate%20Build/badge.svg)

# Simple Api Client

A simple API client for connecting to remote services.

## Features

Along with common methods for creating and performing Json based API
requests, this library supports the following extra features.

* Convenience methods for adding Basic and Bearer auth headers.
* A convenience method for adding signed cookies.
* A timeout limit for all requests.
* A global or per-request retry limit to retry an API request if it fails.
* Uses a best effort approach to deal with malformed Json returned from an API endpoint.
* Each response is guaranteed to contain a status code and well formed parsed Json data.
    * If something goes wrong, an error message will always be included in the data.
* Fully supports returning binary data (as bytes) from an API request.
* handles rate limiting when performing an API request. These requests can be configured to be retried before raising an error.

## Installation

Install and update using `pipenv`

```bash
pip install -U simple-api-client
```

## Usage

### Simple use-case

```python
from simple_api_client import ApiClient
from logging import Logger


logger = Logger("simple-logger", level="DEBUG")
client = ApiClient("http://www.example.com", logger)

response = client.get("/example/endpoint")

if response.status_code == 200:
    print(response.data)
```

### Creating more specific clients

This client has been created to be as flexible as possible to be used as a
base class for more specific clients. All you uneed to do is extend the
`ApiClient` class and add any suitable methods.

```python
from flask import g
from flask import current_app as app
from simple_api_client import ApiClient


class MyServiceClient(ApiClient):

    def use_cookie_auth(self, data):
        name = app.config.get("COOKIE_NAME")
        signing_key = app.config.get("COOKIE_SIGNING_KEY")
        signing_key_id = "trusted-service"
        payload = {"data": data}
        self.add_signed_cookie(name, payload, signing_key_id, signing_key)

    def get_remote_resource():
        return self.get("/example/endpoint")
```

### A note on security

It's import to understand that when a client is initialised with headers and
cookies, these will remain set for the lifetime of the client or until
manually unset. If you don't want this state to remain in-between requests,
it's important to take action to reset the client. In a
[Flask](https://flask.palletsprojects.com/) application this is easily
achieved by assigning the client to the special ['g'
object](https://flask.palletsprojects.com/en/1.1.x/api/#flask.g).

```python
from flask import g
from flask import current_app as app
from simple_api_client import ApiClient


@app.before_request
def setup_api_client():
    g.client = ApiClient("http://www.example.com", app.logger)
```

Then in order to use it, import ['g'](https://flask.palletsprojects.com/en/1.1.x/api/#flask.g)

```python
from flask import g


response = g.client.get("/example/endpoint")
```

The benefit of this pattern is that the client is reset for every flask request so you don't need to worry about stale data in the client.

## Development

__The build pipeline require your tests to pass and code to be formatted__

Make sure you have Python 3.x installed on your machine (use [pyenv](https://github.com/pyenv/pyenv)).

Install the dependencies with [pipenv](https://github.com/pypa/pipenv) (making sure to include dev and pre-release packages):

```bash
pipenv install --dev --pre
```

Configure your environment:

```bash
pipenv shell && export PYTHONPATH="$PWD"
```

Run the tests:

```bash
pytest
```

Or with logging:

```bash
pytest -s
```

Or tests with coverage:

```bash
pytest --cov=./
```

Format the code with [Black](https://github.com/psf/black):

```bash
black $PWD
```

## Releases

Cleanup the (.gitignored) `dist` folder (if you have one):

```bash
rm -rf dist
```

Notch up the version number in `setup.py` and build:

```bash
python3 setup.py sdist bdist_wheel
```

Push to PyPi (using the ScholarPack credentials when prompted)

```bash
python3 -m twine upload --repository-url https://upload.pypi.org/legacy/ dist/*
```

# Links
* Releases: https://pypi.org/project/simple-api-client/
* Code: https://github.com/ScholarPack/simple-api-client/
