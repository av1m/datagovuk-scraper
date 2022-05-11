# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="datagovuk",
    version="1.0.0",
    packages=find_packages(),
    author="av1m",
    author_email="a@avim.eu",
    install_requires=["requests", "beautifulsoup4", "aiohttp"],
    description="Scrap public data from data.gov.uk without an API KEY",
    include_package_data=True,
    url="http://github.com/av1m/datagovuk-scraper",
    entry_points={"console_scripts": ["datagovuk = datagovuk.__main__:main"]},
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
    ],
)
