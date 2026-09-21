# Web Scraper — Books to Scrape

## Objective
A beginner-friendly Python web scraper that collects book data (title,
price, rating, availability) from a public website, cleans it, saves it
as a CSV, and prints an automated summary report every time it runs.

## Website/Resource Used
**[Books to Scrape](https://books.toscrape.com)** — a site built and
hosted specifically for people to practice web scraping on. It:
- Requires no login and no API key
- Has stable, simple HTML
- Explicitly allows scraping in its `robots.txt`
- Has plenty of structured data (title, price, rating, stock status)

The scraper collects data from the first 5 pages of the book catalogue
(~100 books).

## Technologies Used
- **Python 3**
- **requests** — for making HTTP requests
- **BeautifulSoup (bs4)** — for parsing HTML
- **pandas** — for cleaning data and generating statistics

## How Rate Limiting Works
After every successful page request, the script pauses for
`RATE_LIMIT_SECONDS` (1.5 seconds) before the next request is made.
This spreads requests out over time instead of hitting the server as
fast as possible, which is more respectful to the website.

## How Retry Logic Works
Each page request is attempted up to `MAX_RETRIES` (3) times. If a
request fails (timeout, connection error, or an HTTP error status),
the script waits a short, increasing amount of time (a simple backoff)
and tries again. If all attempts fail, that page is skipped and the
scraper moves on instead of crashing.

## What Data Is Extracted
For every book:
- `title` — the book's full title
- `url` — direct link to the book's page
- `price_gbp` — price in GBP, as a number
- `rating_out_of_5` — star rating (1–5), converted from a word like
  "Three" into the number 3
- `availability` — stock status text (e.g. "In stock")
- `category` — a placeholder category field

## How to Install Dependencies
```bash
pip install -r requirements.txt
```

## How to Run the Scraper
```bash
python scraper.py
```
This will:
1. Fetch and parse the catalogue pages
2. Save the cleaned data to `output.csv`
3. Print a summary report to the terminal

## Example Output
```
========================================
WEB SCRAPER SUMMARY REPORT
========================================
Run time: 2026-09-17 13:47:24

Records scraped: 98
Columns: 6

Column names:
  - title
  - url
  - price_gbp
  - rating_out_of_5
  - availability
  - category

Missing values per column:
  - title: 0
  - url: 0
  - price_gbp: 0
  - rating_out_of_5: 0
  - availability: 0
  - category: 0

Duplicate records: 0

Basic statistics for numerical columns:
       price_gbp  rating_out_of_5
count      98.00            98.00
mean       35.42             2.92
...
========================================
```

> Note: `output.csv` in this repo contains a small sample of rows
> (generated the same way the real run would) so the file structure is
> visible without running the scraper. Running `scraper.py` yourself
> will regenerate it with the full, live dataset.

## Ethical / Responsible Scraping Note
This project only scrapes a site that is explicitly meant for
scraping practice, does not require login or bypass any access
controls, respects `robots.txt`, and adds delays between requests so
it never overloads the server. No personal or private data is
collected — everything gathered is public product information.
