catholic-mass-readings
=====

Welcome to the catholic-mass-readings documentation! Here you will find links to the core modules and examples of how to use each.


A Python package that enables converting a US Zip Code into a timezone.

Provides an API for scraping the web page from `Daily Readings <https://bible.usccb.org/bible/readings/>`_ website of United States Conference of Catholic Bishops.

Modules
-------

If there is functionality that is missing or an error in the docs, please open a new issue `here <https://github
.com/rcolfin/catholic-mass-readings/issues>`_.

.. toctree::
    :maxdepth: 1

    catholic_mass_readings/constants
    catholic_mass_readings/models
    catholic_mass_readings/usccb

Install
-------

To install catholic-mass-readings from PyPI, use the following command:

    $ pip install catholic-mass-readings

You can also clone the repo and run the following command in the project root to install the source code as editable:

    $ pip install -e .

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Examples
-----------------

The following example queries for the mass on a particular date:

.. code-block:: Python
    import asyncio
    import datetime

    from catholic_mass_readings import USCCB, models

    async with USCCB() as usccb:
        mass = await usccb.get_mass(datetime.date(2024, 12, 25), models.MassType.VIGIL)
        print(mass)

The following example queries for a range of Sunday masses:

.. code-block:: Python
    async with USCCB() as usccb:
        dates = usccb.get_sunday_mass_dates(datetime.date(2024, 12, 25), datetime.date(2025, 1, 25))
        tasks = [usccb.get_mass_from_date(dt, types) for dt in dates]
        responses = await asyncio.gather(*tasks)
        masses = [m for m in responses if m]
        masses.sort(key=lambda m: m.date.toordinal() if m.date else -1)
        for mass in masses:
            end = "\n" if mass is masses[-1] else "\n\n"
            print(mass, end=end)

To query for a range of masses (step how you want to):

.. code-block:: Python
    async with USCCB() as usccb:
        dates = usccb.get_mass_dates(datetime.date(2024, 12, 25), datetime.date(2025, 1, 25), step=datetime.timedelta(days=1))
        tasks = [usccb.get_mass_from_date(dt) for dt in dates]
        responses = await asyncio.gather(*tasks)
        masses = [m for m in responses if m]
        masses.sort(key=lambda m: m.date.toordinal() if m.date else -1)
        for mass in masses:
            end = "\n" if mass is masses[-1] else "\n\n"
            print(mass, end=end)

To query for the available mass types for a particular date:

.. code-block:: Python
    async with USCCB() as usccb:
        mass_types = await usccb.get_mass_types(datetime.date(2024, 12, 25))
        for mass_type in mass_types:
            print(mass_type.name)

.. code-block:: bash

    # To get a mass for a particular date:
    python -m catholic_mass_readings get-mass --date 2024-12-25 --type vigil

    # To query for a range of Sunday masses:
    python -m catholic_mass_readings get-sunday-mass-range --start 2024-12-25 --end 2025-01-01

    # To query for a range of masses (step how you want to):
    python -m catholic_mass_readings get-mass-range --start 2024-12-25 --end 2025-01-01 --step 7

    # To query for a list of mass types on a particular date:
    python -m catholic_mass_readings get-mass-types --date 2025-12-25

    # or saving to a file...

    # To get a mass for a particular date:
    python -m catholic_mass_readings get-mass --date 2024-12-25 --type vigil --save mass.json

    # To query for a range of Sunday masses:
    python -m catholic_mass_readings get-sunday-mass-range --start 2024-12-25 --end 2025-01-01 --save mass.json

    # To query for a range of masses (step how you want to):
    python -m catholic_mass_readings get-mass-range --start 2024-12-25 --end 2025-01-01 --step 7 --save mass.json
