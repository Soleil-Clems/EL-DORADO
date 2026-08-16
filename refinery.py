import sys, os, shutil
import requests
import yaml
import json
import logging
from time import sleep
import pandas as pd
from dateutil import parser
import datetime


def is_valid_date_flexible(date_string):
    try:
        parser.parse(date_string)
        return True
    except (ValueError, OverflowError):
        return False


with open("config.yaml") as f:
    config = yaml.safe_load(f)

books = []
option = sys.argv[1]


def extract():
    for page in range(1, config["api"]["pages"] + 1):

        data = None

        for attempt in range(3):
            try:
                r = requests.get(
                    f"{config['api']['base_url']}/?language={config['api']['language']}&page={page}",
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                break

            except requests.exceptions.Timeout:
                logging.error(f"Timeout page {page}, attempt {attempt+1}")

            except requests.exceptions.ConnectionError:
                logging.error(f"Network error page {page}, attempt {attempt+1}")

            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP error page {page}: {e}")
                break

            except Exception as e:
                logging.error(f"Unknown error page {page}: {e}")

            sleep(2)

        if data is None:
            logging.error(f"Page {page} skipped after retries")
            continue

    with open(config["bronze_path"] + "/api_books.json", "w") as f:
        json.dump(data["results"], f, ensure_ascii=False, indent=4)

    old_filename = os.path.join("data/sources", "book_reviews_messy.csv")
    new_filename = os.path.join(config["bronze_path"], "reviews.csv")
    shutil.copy(old_filename, new_filename)


def transform():
    data = pd.read_csv(config["bronze_path"] + "/reviews.csv", encoding="utf-8")
    df = pd.DataFrame(data)
    reviews_df= transform_rewies_csv(df)
    api_df = pd.DataFrame(transform_books_json())
    api_df = api_df.rename(columns={"id": "book_id"})
    merged = api_df.merge(reviews_df, on="book_id", how="left")
    print(merged)
    


def transform_books_json():
    with open(config["bronze_path"] + "/api_books.json", "r", encoding='utf-8') as f:
        data = json.load(f)
        # print(json.dumps(books, indent=4))


    for result in data:
        authors = result.get("authors", [])

        author = (
            authors[0]
            if authors
            else {
                "name": None,
                "birth_year": None,
                "death_year": None,
            }
        )


        books.append(
            {
                "id": result["id"],
                "title": result["title"],
                "authors_name": author["name"],
                "authors_birth_year": author["birth_year"],
                "authors_death_year": author["death_year"],
                "languages": result["languages"][0],
                "subjects": result["subjects"],
                "download_count": result["download_count"],
            }
        )

    return books

def transform_rewies_csv(df):
    # dropna for removing empty values or NA values
    df.dropna(inplace=True)

    df["title"] = df["title"].str.strip()
    df["reviewer"] = df["reviewer"].str.strip()
    df["reviewer"] = df["reviewer"].str.capitalize()
    df["recommend"] = df["recommend"].str.lower()

    df["my_rating"] = df["my_rating"].astype(int)
    df["book_id"] = df["book_id"].astype(int)

    mapping = {
        "yes": True,
        "y": True,
        "n": False,
        "no": False,
        "": None,
    }

    df["recommend"] = df["recommend"].map(mapping)

    for i in df.index:
        if df.loc[i, "my_rating"] > 5 or df.loc[i, "my_rating"] < 1:
            df.drop(i, inplace=True)

    valid_mask = df["date_added"].apply(is_valid_date_flexible)
    rejected_dates = df[~valid_mask]
    df = df[valid_mask].copy()
    df["date_added"] = df["date_added"].apply(
        lambda d: parser.parse(d).strftime("%Y-%m-%d")
    )

    df.drop_duplicates(inplace=True)

    return df


def options(option):
    match option:
        case "extract":
            extract()
        case "transform":
            print(transform())
        case "load":
            print("load")
        case "stats":
            print("stat")
        case "run":
            return print("run all refinery")

        case _:
            transform_books_json()
            print("This option don't exist")


options(option)
