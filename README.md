# Simple Api Client

A simple API client for connecting to remote services.

## Installation

Install and update using `pipenv`

```bash
pip install -U simple-api-client
```

## Usage

```python
from simple_api_client import ApiClient
from logging import Logger


logger = Logger("simple-logger", level="DEBUG")
client = ApiClient("http://www.example.com", logger)

response = client.get("/example/endpoint")

if response.status_code == 200:
    print(response.data)
```

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
