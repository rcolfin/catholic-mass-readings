# catholic-mass-readings

[![CI Build](https://github.com/rcolfin/catholic-mass-readings/actions/workflows/ci.yml/badge.svg)](https://github.com/rcolfin/catholic-mass-readings/actions/workflows/ci.yml)
[![PyPI Version](https://img.shields.io/pypi/v/catholic-mass-readings)](https://pypi.python.org/pypi/catholic-mass-readings)
[![versions](https://img.shields.io/pypi/pyversions/catholic-mass-readings.svg)](ttps://github.com/rcolfin/catholic-mass-readings)

Provides an API for scraping the web page from [Daily Readings](https://bible.usccb.org/bible/readings/) website of United States Conference of Catholic Bishops.

## Development

### Setup Python Environment:

Run [scripts/console.sh](../scripts/console.sh) poetry install

### If you need to relock:

Run [scripts/lock.sh](../scripts/lock.sh)

### Run code

Run [scripts/console.sh](../scripts/console.sh) poetry run catholic_mass_readings


## API Usage:

```python
import asyncio
import datetime

from catholic_mass_readings import USCCB

# To get a mass for a particular date:
async with USCCB() as usccb:
    mass = await usccb.get_mass_from_date(datetime.date(2024, 12, 25))
    print(mass.dumps())

# To query for a range of Sunday masses:
async with USCCB() as usccb:
    masses: list[models.Mass] = []
    dates = usccb.get_sunday_mass_dates(datetime.date(2024, 12, 25), datetime.date(2024, 1, 25))
    for task in asyncio.as_completed([usccb.get_mass_from_date(dt) for dt in dates]):
        mass = await task
        if mass:
            print(mass.dumps())

    masses.sort(key=lambda m: m.date.toordinal() if m.date else -1)
    print(mass.dumps())

# To query for a range of masses (step how you want to):
async with USCCB() as usccb:
    masses: list[models.Mass] = []
    dates = usccb.get_mass_dates(datetime.date(2024, 12, 25), datetime.date(2024, 1, 25), step=datetime.timedelta(days=1))
    for task in asyncio.as_completed([usccb.get_mass_from_date(dt) for dt in dates]):
        mass = await task
        if mass:
            print(mass.dumps())

    masses.sort(key=lambda m: m.date.toordinal() if m.date else -1)
    print(mass.dumps())
```

As a CLI

```sh
# To get a mass for a particular date:
python -m catholic_mass_readings get-mass --date 2024-12-25

# To query for a range of Sunday masses:
python -m catholic_mass_readings get-sunday-mass-range --start 2024-12-25 --end 2025-01-01

# To query for a range of masses (step how you want to):
python -m catholic_mass_readings get-mass-range --start 2024-12-25 --end 2025-01-01 --step 7
```

or saving to a file...

```sh
# To get a mass for a particular date:
python -m catholic_mass_readings get-mass --date 2024-12-25 --save mass.json

# To query for a range of Sunday masses:
python -m catholic_mass_readings get-sunday-mass-range --start 2024-12-25 --end 2025-01-01 --save mass.json

# To query for a range of masses (step how you want to):
python -m catholic_mass_readings get-mass-range --start 2024-12-25 --end 2025-01-01 --step 7 --save mass.json
```

## Installation

To install catholic-mass-readings from PyPI, use the following command:

    $ pip install catholic-mass-readings

You can also clone the repo and run the following command in the project root to install the source code as editable:

    $ pip install -e .

## Documentation
The documentation for `catholic-mass-readings` can be found [here](https://rcolfin.github.io/catholic-mass-readings/) or in the project's docstrings.
