"""
scraper.py
------------------------------------------------------
A beginner-friendly web scraper for Books to Scrape
(https://books.toscrape.com), a website that is built
and maintained specifically for people to practice
web scraping on. It requires no login, no API key, and
its robots.txt allows scraping.

What it does:
  1. Visits multiple pages of the book catalogue.
  2. Extracts the title, price, star rating, availability,
     and category for every book.
  3. Cleans the data and saves it to output.csv.
  4. Prints an automated summary report of the run.

Run it with:
    python scraper.py
------------------------------------------------------
"""

import time
import sys
import random
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pandas as pd


# ----------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
NUM_PAGES_TO_SCRAPE = 5          # keep it small & polite for a student project
REQUEST_TIMEOUT = 10             # seconds to wait for a response
MAX_RETRIES = 3                  # how many times to retry a failed request
RATE_LIMIT_SECONDS = 1.5         # pause between requests, to be respectful
OUTPUT_CSV = "output.csv"

# A "real" browser-like User-Agent. Sites are more likely to serve
# normal HTML (instead of blocking us) when we identify ourselves
# like a real browser rather than the default python-requests agent.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Star ratings on the site are written as CSS classes like
# "star-rating Three". This maps the word to a number so we can
# store it as a proper numeric column.
RATING_WORDS = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def create_session() -> requests.Session:
    """
    Create and configure a requests.Session with our custom
    headers already attached. Using a Session (instead of calling
    requests.get directly) lets us reuse the same TCP connection
    for multiple requests, which is faster and more polite to the
    server than opening a new connection every time.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_page(session: requests.Session, url: str) -> str | None:
    """
    Fetch a single page with:
      - a timeout, so we never hang forever waiting on a slow server
      - retry logic, so a temporary network hiccup doesn't kill the
        whole scrape
      - rate limiting, so we don't hammer the server with requests

    Returns the HTML text on success, or None if every attempt fails.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)

            # Raise an exception for HTTP error codes (4xx / 5xx)
            # so they get handled in the except block below.
            response.raise_for_status()

            # Be a polite scraper: wait a bit before the *next*
            # request is made by the caller.
            time.sleep(RATE_LIMIT_SECONDS)

            return response.text

        except requests.exceptions.RequestException as error:
            print(f"  [!] Attempt {attempt}/{MAX_RETRIES} failed for {url}: {error}")

            if attempt < MAX_RETRIES:
                # Small increasing delay before trying again
                # (a very simple form of "backoff").
                backoff = RATE_LIMIT_SECONDS * attempt
                time.sleep(backoff)
            else:
                print(f"  [x] Giving up on {url} after {MAX_RETRIES} attempts.")
                return None

    return None


def parse_book_card(book_tag) -> dict:
    """
    Given one <article class="product_pod"> BeautifulSoup tag
    (one book "card" on the listing page), extract the fields
    we care about and return them as a dictionary.
    """
    # --- Title ---
    # The title is stored in the "title" attribute of the <a> tag
    # inside the <h3>, because the visible text is often truncated
    # with "..." on the page.
    title_tag = book_tag.h3.a
    title = title_tag["title"].strip()

    # --- URL ---
    relative_url = title_tag["href"]
    full_url = "https://books.toscrape.com/catalogue/" + relative_url.replace("../../../", "")

    # --- Price ---
    # Example raw text: "Â£51.77" -> we strip everything except digits and dot
    raw_price = book_tag.find("p", class_="price_color").text
    price_text = "".join(ch for ch in raw_price if ch.isdigit() or ch == ".")
    price = float(price_text) if price_text else None

    # --- Star rating ---
    # The rating is encoded as a CSS class, e.g. class="star-rating Three"
    rating_classes = book_tag.find("p", class_="star-rating")["class"]
    rating_word = rating_classes[1] if len(rating_classes) > 1 else None
    rating = RATING_WORDS.get(rating_word)

    # --- Availability ---
    availability = book_tag.find("p", class_="instock availability").text.strip()

    return {
        "title": title,
        "url": full_url,
        "price_gbp": price,
        "rating_out_of_5": rating,
        "availability": availability,
    }


def scrape_books() -> list[dict]:
    """
    Loop through NUM_PAGES_TO_SCRAPE catalogue pages, parse every
    book on each page, and return a list of dictionaries (one per
    book). Category is added afterwards for simplicity, since the
    catalogue pages don't show it directly per-book.
    """
    session = create_session()
    all_books = []

    for page_number in range(1, NUM_PAGES_TO_SCRAPE + 1):
        url = BASE_URL.format(page_number)
        print(f"[*] Fetching page {page_number}: {url}")

        html = fetch_page(session, url)
        if html is None:
            # Skip this page if it never succeeded, but keep going
            # with the rest of the scrape.
            continue

        soup = BeautifulSoup(html, "html.parser")
        book_cards = soup.find_all("article", class_="product_pod")

        print(f"    -> found {len(book_cards)} books on this page")

        for card in book_cards:
            try:
                book_data = parse_book_card(card)
                # A very light "category" placeholder, since the
                # listing page alone doesn't expose it. Genre-level
                # scraping would mean visiting each book's own page,
                # which we skip to keep the project simple.
                book_data["category"] = "General"
                all_books.append(book_data)
            except (AttributeError, KeyError, TypeError) as parse_error:
                # If one book's HTML is malformed/unexpected, skip
                # just that book instead of crashing the whole run.
                print(f"    [!] Skipped a book due to a parsing error: {parse_error}")

    return all_books


def clean_and_save(raw_books: list[dict]) -> pd.DataFrame:
    """
    Load the scraped data into a pandas DataFrame, clean it up,
    and save it to OUTPUT_CSV. Returns the cleaned DataFrame so
    the caller can use it to build the summary report.
    """
    df = pd.DataFrame(raw_books)

    if df.empty:
        print("[!] No data was scraped, nothing to save.")
        return df

    # Remove exact duplicate rows (e.g. if a book appeared twice).
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed:
        print(f"[*] Removed {removed} duplicate row(s).")

    # Drop rows where the title or price is missing, since those
    # are the two fields that matter most for this dataset.
    df = df.dropna(subset=["title", "price_gbp"])

    # Reset the index after dropping rows so it stays clean (0,1,2,...).
    df = df.reset_index(drop=True)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"[*] Saved {len(df)} rows to {OUTPUT_CSV}")

    return df


def print_summary_report(df: pd.DataFrame) -> None:
    """
    Print a clear, human-readable summary of the scraped dataset.
    This runs automatically every time the scraper finishes.
    """
    print("\n" + "=" * 40)
    print("WEB SCRAPER SUMMARY REPORT")
    print("=" * 40)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if df.empty:
        print("No records were scraped.")
        print("=" * 40)
        return

    print(f"\nRecords scraped: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumn names:")
    for col in df.columns:
        print(f"  - {col}")

    print("\nMissing values per column:")
    missing = df.isnull().sum()
    for col, count in missing.items():
        print(f"  - {col}: {count}")

    duplicate_count = df.duplicated().sum()
    print(f"\nDuplicate records: {duplicate_count}")

    numeric_df = df.select_dtypes(include="number")
    if not numeric_df.empty:
        print("\nBasic statistics for numerical columns:")
        print(numeric_df.describe().round(2).to_string())
    else:
        print("\nBasic statistics: no numerical columns found.")

    print("\n" + "=" * 40)


def main():
    print("Starting Books to Scrape scraper...\n")

    try:
        raw_books = scrape_books()
        cleaned_df = clean_and_save(raw_books)
        print_summary_report(cleaned_df)

    except KeyboardInterrupt:
        print("\n[!] Scraping interrupted by user. Exiting gracefully.")
        sys.exit(1)

    except Exception as unexpected_error:
        # Catch-all so an unexpected error never crashes with an
        # ugly traceback -- we print something useful instead.
        print(f"\n[x] An unexpected error occurred: {unexpected_error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
