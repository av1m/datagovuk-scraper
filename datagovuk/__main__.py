# coding: utf-8

import argparse
import asyncio
import logging
import time

from datagovuk.scraper import Scraper


async def run():
    """Get the parser and run the scraper."""
    # Get the parser
    parser = argparse.ArgumentParser(description="Scrap public data from data.gov.uk")
    parser.add_argument("--query", "-q", type=str, help="Search query", required=True)
    parser.add_argument(
        "--number-record",
        "-n",
        type=int,
        help="Number of records to fetch, must be a valid number",
        required=True,
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file",
        default="csv",
        choices=["csv", "ods", "html", "pdf", "xls", "zip"],
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Put the logger in debug mode",
        action="store_const",
        dest="log_level",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Put the logger in info mode",
        dest="log_level",
        action="store_const",
        const=logging.INFO,
    )
    args = parser.parse_args()
    if not args.query:
        parser.print_help()
        return
    # Set up logging
    logging.basicConfig(
        level=args.log_level,
        format="[%(name)s] [%(levelname)s] - %(message)s ",
    )
    # Run the scraper
    scraper = Scraper(query=args.query, format_type=args.output)
    try:
        await scraper.get_datasets(count=args.number_record)
        await scraper.download()
        scraper.save_metadata()
    finally:
        await scraper.session.close()


def main():
    """Main function."""
    start = time.time()
    asyncio.run(run())
    print(f"Execution time with async: {time.time()- start}")


if __name__ == "__main__":
    main()
