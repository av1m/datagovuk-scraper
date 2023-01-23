# datagovuk-scraper

[![Python3.10](https://img.shields.io/badge/Python-3.10-blue)](https://docs.python.org/3/whatsnew/3.10.html)
[![MIT License](https://img.shields.io/bower/l/bootstrap)](https://github.com/av1m/datagovuk-scraper/blob/master/LICENSE)

Scrap public data from data.gov.uk without an API KEY

## Get started 🎉

1. Clone the project

    ```bash
    git clone https://github.com/av1m/datagovuk-scraper
    cd datagovuk-scraper
    ```

2. Install dependencies

    ```bash
    pip install -r requirements.txt
    ```

3. Run the project 🚀  
    You can run the project in different ways.

    * To get started quickly, you can use the [notebook](get-started-sample.ipynb).
    * Plus, you can use the [command line](#cli)
    * Or, directly in your code by importing the `datagovuk` module.

## CLI Usage 📖

> 💡 You can directly install dependencies instead of clone the repository :
>
> ```bash
> pip install git+https://github.com/av1m/datagovuk-scraper.git
> ```
>

To run the project from the command line, use the command `datagovuk`.

Here is the list of available commands:

```bash
datagovuk --help
usage: __main__.py [-h] --query QUERY --number-record NUMBER_RECORD [--output {csv,ods,html,pdf,xls,zip}] [-d] [-v]

Scrap public data from data.gov.uk

options:
  -h, --help              show this help message and exit
  --query, -q             Search query (required)
  
  --number-record, -n     Number of records to fetch, must be a valid number (required)
  --output, -o            Output file (must be csv,ods,html,pdf,xls,zip). Default is csv
  -d, --debug             Put the logger in debug mode (default: Warning)
  -v, --verbose           Put the logger in info mode (default: Warning)
```

And, here an example of some examples:

* Get the first 10 records for the query `"house"` and with only CSV file as output (debug mode activated):

    ```bash
    datagovuk -q house -n 10 -o csv -d
    ```
