import sys
import requests
import yaml
import json

with open("config.yaml") as f:
  config = yaml.safe_load(f)
  
books=[]
option = sys.argv[1]

def extract():
  for page in range(1,config["api"]["pages"]+1):
      
    r = requests.get(f"{config['api']['base_url']}/?language={config['api']['language']}&page={page}")
    data= r.json()


    for result in data['results']:
      if not result["authors"]:
        result["authors"].append({
            "name": None,
            "birth_year": None,
            "death_year": None,
        })
        
      books.append({
        "id": result["id"],
        "title": result["title"],
        "authors_name": result["authors"][0]["name"] or None,
        "authors_birth_year": result["authors"][0]["birth_year"] or None,
        "authors_death_year": result["authors"][0]["death_year"] or None,
        "languages": result["languages"][0],
        "subjects": result["subjects"],
        "download_count": result["download_count"],
      })
  
  with open("data/bronze/api_books.json", "w") as f:
    json.dump(books, f, ensure_ascii=False, indent=4)



def options(option):
  match option:
        case "extract":
            print(extract())
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