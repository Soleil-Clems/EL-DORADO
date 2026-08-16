import sys, os, shutil
import requests
import yaml
import json
import logging
from time import sleep
import pandas as pd
from dateutil import parser
import numpy as np
import sqlite3
import db


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
    all_books = []
    for page in range(1, config["api"]["pages"] + 1):

        data = None

        for attempt in range(3):
            try:
                r = requests.get(
                    f"{config['api']['base_url']}/?languages={config['api']['languages']}&page={page}",
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                all_books.extend(data["results"])
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
        json.dump(all_books, f, ensure_ascii=False, indent=4)

    old_filename = os.path.join("data/sources", "book_reviews_messy.csv")
    new_filename = os.path.join(config["bronze_path"], "reviews.csv")
    shutil.copy(old_filename, new_filename)


def transform():
    data = pd.read_csv(config["bronze_path"] + "/reviews.csv", encoding="utf-8")
    df = pd.DataFrame(data)
    reviews_df = transform_rewies_csv(df)
    api_df = pd.DataFrame(transform_books_json())
    api_df = api_df.rename(columns={"id": "book_id"})
    merged = api_df.merge(reviews_df, on="book_id", how="left")
    clean_df = merged.replace({np.nan: None})
    clean_df["author_birth_year"] = clean_df["author_birth_year"].astype("Int64")
    clean_df["author_death_year"] = clean_df["author_death_year"].astype("Int64")
    clean_df["my_rating"] = clean_df["my_rating"].astype("Int64")
    clean_df = clean_df.rename(columns={"title_x": "title"})
    clean_df = clean_df.drop(columns=["title_y"])
    clean_df = clean_df.to_dict(orient="records")
    with open(config["silver_path"] + "/clean.json", "w") as f:
        json.dump(clean_df, f, ensure_ascii=False, indent=4)


def transform_books_json():
    with open(config["bronze_path"] + "/api_books.json", "r", encoding="utf-8") as f:
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
                "author": author["name"],
                "author_birth_year": author["birth_year"],
                "author_death_year": author["death_year"],
                "language": result["languages"][0],
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


def load():
    
    connection = sqlite3.connect(config["db_path"])
    db.create_schema(connection)
    cursor = connection.cursor()
    with open(config["silver_path"] + "/clean.json", "r", encoding="utf-8") as f:
        clean_json = json.load(f)

    for book in clean_json:
        cursor.execute(
            "INSERT OR REPLACE INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                book["book_id"],
                book["title"],
                book["author"],
                book["author_birth_year"],
                book["author_death_year"],
                book["language"],
                json.dumps(book["subjects"]),  # <- la liste sérialisée en JSON string
                book["download_count"],
                book["my_rating"],
                book["date_added"],
                book["reviewer"],
                book["recommend"],
            ),
        )


    connection.commit()
    connection.close()


def options(option):
    match option:
        case "extract":
            extract()
        case "transform":
            transform()
        case "load":
            load()
        case "stats":
            print("stat")
        case "run":
            extract()
            transform()
            load()

        case _:
            transform_books_json()
            print("This option don't exist")


options(option)
