import json
import requests
from pandas import ExcelWriter, DataFrame


class Category:
    def __init__(self, id_: int, name: str, level: int):
        self.id = id_
        self.name = name
        self.level = level

    def to_dict(self):
        return {
            "ID": self.id,
            "name": self.name,
            "level": self.level,
        }


def parse_categories(data: list, level=1) -> list:
    categories = []
    for item in data:
        cat = Category(id_=item["id"], name=item["name"], level=level)
        categories.append(cat)

        if "childs" in item:
            children = parse_categories(item["childs"], level + 1)
            categories.extend(children)

        elif "childs" not in item:
            cat.level = 99

    return categories


def main():
    response = requests.get(
        "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-by-ru-v3.json"
    )
    raw_data = json.loads(response.text)
    grouped = {}
    for block in raw_data:
        root_name = block["name"]
        cats = parse_categories([block])
        grouped[root_name] = cats

    with ExcelWriter("wildberries_categories.xlsx", engine="openpyxl") as writer:
        for sheet_name, categories in grouped.items():
            df = DataFrame([cat.to_dict() for cat in categories])
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)


if __name__ == "__main__":
    main()
