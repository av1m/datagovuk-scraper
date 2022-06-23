# coding: utf-8

"""Scrap public data from data.gov.uk.

This module provides a scraper class that can be used to fetch public
data from data.gov.uk asynchronously.
"""

import asyncio
import json
import logging
import math
import os
import time
from pathlib import Path

import requests
from aiohttp import ClientResponse, ClientSession
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm

logger = logging.getLogger(__name__)


class Dataset:
    """A representation of a dataset in the database of data.gov.uk."""

    def __init__(self, dataset_id: str, title: str, url: str, soup: BeautifulSoup):
        """Initialize the dataset.

        Example:
            >>> dataset = Dataset(
                    dataset_id="a7d72401-5c0c-464e-be7b-7a332a138ffd",
                    title="Spend in Companies House",
                    url="https://data.gov.uk/dataset/a7d72401-5c0c-464e-be7b-7a332a138ffd/spend-in-companies-house",
                    soup=soup,
                )

        :param soup: An element of the datacenter
        :type soup: BeautifulSoup
        """
        self.soup = soup
        self.id = dataset_id  # pylint: disable=invalid-name
        self.title = title
        self.url = url
        self.metadata = self.get_metadata()
        self.files = self.get_files()

    def get_metadata(self) -> dict:
        """Return a dictionary with metadata about the dataset.

        The keys are the names of the metadata fields.

        Example:
            >>> dataset.get_metadata()
            >>> {'published_by': 'Companies House',
                 'last_updated': '18 February 2014',
                 'title': 'Spend in Companies House',
                 'description': 'A monthly updated [...]',
                 'licence': 'Open Government Licence'}

        :return: dict
        :rtype: dict
        """
        metadata = {}
        metadata["published_by"] = self.soup.find(
            "dd", {"property": "dc:creator"}
        ).text.strip()
        metadata["last_updated"] = self.soup.find(
            "dd", {"property": "dc:date"}
        ).text.strip()
        metadata["title"] = self.soup.find("h1", {"property": "dc:title"}).text.strip()
        metadata["description"] = self.soup.find(
            "div", {"property": "dc:description"}
        ).text.strip()
        metadata["licence"] = self.soup.find(
            "dd", {"property": "dc:rights"}
        ).text.strip()
        return metadata

    def get_files(self) -> list[dict]:
        """Return a list of dictionaries with information about the files.

        Example:
            >>> dataset.get_files()
            >>> [{'url': 'http://www.companieshouse.gov.uk/about/miscellaneous/GovernmentProcurementCardSpendNovember2013.csv',
                  'name': 'Expenditure by Government Procurement Cards November 2013',
                  'format': 'CSV',
                  'file_added': '18 February 2014'
                }, ...]

        :return: list[dict]
        :rtype: list[dict]
        """
        csv_urls = []
        tds = self.soup.find_all("td", class_="govuk-table__cell")
        assert len(tds) % 4 == 0, "There should be four columns per row"
        for i in range(4, len(tds) + 1, 4):
            td_tag = tds[i - 4 : i]
            csv_urls.append(
                {
                    "url": td_tag[0].a["href"],
                    "name": td_tag[0].a.contents[2].strip(),
                    "format": td_tag[1].text.strip(),
                    "file_added": td_tag[2].text.strip(),
                }
            )
        return csv_urls

    @staticmethod
    async def download_file(session: ClientSession, url: str, path: Path) -> None:
        """Download a file.

        Example:
            >>> dataset.download_file(
                    session=session,
                    url="http://www.companieshouse.gov.uk/about/miscellaneous/GovernmentProcurementCardSpendNovember2013.csv",
                    path=Path("/path/to/file.csv"),
                )

        :param session: Aiohttp session
        :type session: ClientSession
        :param file: A dictionary with information about the file.
        :type file: dict
        :return: None
        :rtype: None
        """
        async with session.get(url) as response:
            content = await response.read()
            # Save the file
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as file:
                file.write(content)

    def download_files(self, session: ClientSession) -> list:
        """Download all the files of the dataset.

        :param session: Aiohttp session
        :type session: ClientSession
        :return: A list with the element downloaded (used for the asyncio.gather)
        :rtype: list
        """
        files = []  # use to gather with asyncio.gather
        for file in self.files:
            filename: Path = (
                Path.home() / "datagovuk" / self.id / file["url"].split("/")[-1]
            )
            files.append(self.download_file(session, file["url"], filename))
        return files

    def to_json(self) -> dict:
        """Get the dataset as a dictionary.

        Example:
            >>> dataset = Dataset("id1", "title1", "url1", soup)
            >>> dataset.to_json()
            {"id": "id1", "title": "title1", "url": "url1", "metadata": "...", "files": "..."}

        :return: A dictionary with the id, title, url, metadata, and files of the object.
        :rtype: dict
        """
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "metadata": self.metadata,
            "files": self.files,
        }


class Scraper:
    """This class provide a scraper that can be used to fetch public data from
    data.gov.uk asynchronously.

    You need to check the number of records that exist on data.gov.uk.
    If you indicate a number of pages greater than this number, the scraper will stop and throw an exception.

    The data can be downloaded asynchronously and are stored in $HOME/datagovuk/ directory.
    The metadata are also stored in $HOME/datagokuk/ directory.

    The format of the files is CSV by default. You can change the format by setting the format_type attribute.
    Allowed format are ["csv", "ods", "html", "pdf", "xls", "zip"]
    """

    PER_PAGE: int = 20

    def __init__(self, query: str, format_type: str = "CSV") -> None:
        """Initialize the scraper.

        You can search in https://data.gov.uk/search to see the results in preamble.

        Allowed format_type are ["csv", "ods", "html", "pdf", "xls", "zip"]

        Example:
            >>> scraper = Scraper(query="map", format_type="csv")
            >>> await scraper.get_datasets(count=50) # get 50 datasets
            >>> await scraper.download() # download the datasets
            >>> await scraper.save_metadata() # save the metadata

        :param query: The query to search for, e.g. "house"
        :type query: str
        :param format_type: The format of the files, e.g. "CSV"
        :type format_type: str
        """
        assert format_type.lower() in ["csv", "ods", "html", "pdf", "xls", "zip"]
        self.session: ClientSession = ClientSession(
            base_url="https://data.gov.uk/",
            headers={
                # pylint: disable=line-too-long
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:23.0) Gecko/20131011 Firefox/23.0"
            },
        )
        self.query: str = query
        self.format_type: str = format_type
        self.first_page: BeautifulSoup = self.search(page=1, cache_first=False)
        self.length: int = self.get_length()
        self.max_pages: int = math.ceil(self.length / self.PER_PAGE)
        # By default, this list is empty
        self.datasets: list[Dataset] = []

    def search(self, page: int, cache_first: bool = True) -> BeautifulSoup:
        """Research all datasets corresponding to the request.

        :param page: The page to search for, e.g. 1
        :type page: int
        :param cache_first: If True, the first page will be cached
        :type cache_first: bool
        :return: The soup of the page
        :rtype: BeautifulSoup
        """
        # Cache the first page
        if page == 1 and cache_first:
            return self.first_page
        search_response = requests.get(
            url="https://data.gov.uk/search",
            params={
                "q": self.query,
                "filters[format]": self.format_type.upper(),
                "sort": "best",
                "page": page,
            },
        )
        # Check the status
        search_response.raise_for_status()
        logger.info("GET %s", search_response.url)
        return BeautifulSoup(search_response.text, "html.parser")

    async def get_dataset(self, dataset: BeautifulSoup) -> Dataset:
        """Get the dataset from the soup.

        This function is used to transform a BeautifulSoup object (corresponding to a html dataset) into a Dataset object.

        The dataset correspond to a row in the search page of data.gov.uk.

        Example:
            >>> dataset = await scraper.get_dataset(dataset)
            >>> dataset.id
            "a7d72401-5c0c-464e-be7b-7a332a138ffd"

        :param dataset: The soup of the dataset
        :type dataset: BeautifulSoup
        :return: The dataset
        :rtype: Dataset
        """
        dataset_id = dataset.a["href"].split("/")[2]

        dataset_response: ClientResponse = await self.session.get(
            url=f"/dataset/{dataset_id}"
        )
        logger.info("GET dataset %s", dataset_response.url)
        dataset_response.raise_for_status()

        # Create the soup object for the dataset
        dataset_soup: BeautifulSoup = BeautifulSoup(
            await dataset_response.text(), "html.parser"
        )
        return Dataset(
            dataset_id=dataset_id,
            title=dataset.h2.a.text,
            url=dataset.a["href"],
            soup=dataset_soup,
        )

    def get_length(self) -> int:
        """Get the number of datasets matching the query.

        Example (with 50 datasets):
            >>> scraper = Scraper(query="map", format_type="csv")
            >>> scraper.get_length()
            50

        :return: The number of datasets matching the query
        :rtype: int
        """
        results_count = self.first_page.find(
            "span", {"class": "govuk-body-s govuk-!-font-weight-bold"}
        ).text
        self.length = int(results_count.replace(",", ""))
        # Check how many results we got
        logger.info("Found %s results", self.length)
        return self.length

    async def get_datasets(self, count: int) -> list[Dataset]:
        """Get the datasets matching the query.

        This function will iterate through the pages until it reaches the count.

        Example (with 50 datasets):
            >>> scraper = Scraper(query="map", format_type="csv")
            >>> await scraper.get_datasets(count=50)
            >>> len(scraper.datasets)
            50
            >>> scraper.datasets[0].title
            "Map of the UK" # for example

        :param count: The number of datasets to get, must be less than the number of datasets matching the query
        :type count: int
        :return: The datasets matching the query
        :rtype: list[Dataset]
        """
        assert (
            count <= self.length
        ), "The count (number of records) is larger than the number of datasets available on data.gov.uk"
        pages: int = math.ceil(count / self.PER_PAGE)
        assert pages <= self.max_pages, "The count is larger than the number of pages"
        last_page_item: int = count - ((pages - 1) * self.PER_PAGE)

        datasets = []
        async for page in tqdm(range(1, pages + 1)):
            datasets_containers = self.search(page).find_all(
                "div", {"class": "dgu-results__result"}
            )
            if page == pages:  # Last page
                datasets_containers = datasets_containers[:last_page_item]
            async for dataset in tqdm(datasets_containers):
                datasets.append(self.get_dataset(dataset))
        self.datasets = await asyncio.gather(*datasets)
        return self.datasets

    async def download(self) -> None:
        """Download all datasets.

        This function look in the datasets attribute and download the files.
        The file will be saved in the $HOME/datagovuk directory.

        Example:
            >>> scraper = Scraper(query="map", format_type="csv")
            >>> await scraper.get_datasets(count=50)
            >>> await scraper.download()

        :return: None
        """
        waits = []
        async with ClientSession() as session:
            dataset: Dataset
            async for dataset in tqdm(self.datasets):
                waits.extend(dataset.download_files(session))
            await asyncio.gather(*waits)
            logger.info(
                "Downloaded %s datasets in %s",
                len(self.datasets),
                Path.home() / "datagovuk",
            )

    def save_metadata(self) -> None:
        """Save the metadata for all datasets.

        This function will look in the datasets attribute

        Example:
            >>> scraper = Scraper(query="map", format_type="csv")
            >>> await scraper.get_datasets(count=50)
            >>> scraper.save_metadata()

        :return: None
        """
        filename: Path = (
            Path.home() / "datagovuk" / f"datasets-metadata-{int(time.time())}.json"
        )
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                obj=self.datasets, fp=file, indent=4, default=lambda obj: obj.to_json()
            )
        logger.info("Wrote metadata in %s", filename)
