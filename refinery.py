import sys
import requests
import yaml
import json
import traceback
import logging
from time import sleep

with open("config.yaml") as f:
  config = yaml.safe_load(f)
  
books=[]
option = sys.argv[1]

def extract():
    for page in range(1, config["api"]["pages"] + 1):

        data = None

        for attempt in range(3):
            try:
                r = requests.get(
                    f"{config['api']['base_url']}/?language={config['api']['language']}&page={page}",
                    timeout=30
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

        for result in data.get("results", []):
            authors = result.get("authors", [])

            author = authors[0] if authors else {
                "name": None,
                "birth_year": None,
                "death_year": None,
            }

            books.append({
                "id": result["id"],
                "title": result["title"],
                "authors_name": author["name"],
                "authors_birth_year": author["birth_year"],
                "authors_death_year": author["death_year"],
                "languages": result["languages"][0],
                "subjects": result["subjects"],
                "download_count": result["download_count"],
            })     
    with open("data/bronze/api_books.json", "w") as f:
      json.dump(books, f, ensure_ascii=False, indent=4)

def options(option):
  match option:
        case "extract":
            extract()
        case "transform":
            print("transform")
        case "load":
            print("load")
        case "stats":
            print("stat")
        case "run":
            return print("run all refinery")

        case _:
            print("This option don't exist")

options(option)