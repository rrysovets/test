import json
import asyncio
from curl_cffi.requests import AsyncSession
from pandas import ExcelWriter, DataFrame



class Category:
    def __init__(self, id: int, name: str, level: int = 99, url: str = "", shard: str = "", query: str = ""):
        self.id = id
        self.name = name
        self.level = level
        self.url = url
        self.shard = shard
        self.query = query

    def to_dict(self):
        return {
            "ID": self.id,
            "name": self.name,
            "level": self.level,
        }


async def fetch_filter_categories(session: AsyncSession, shard: str, query: str) -> list[Category]:
    url = f"https://catalog.wb.ru/catalog/{shard}/v8/filters?ab_testing=false&appType=1&{query}&curr=rub&dest=-59202&hide_dtype=13&lang=ru&spp=30"
    try:
        response = await session.get(url, timeout=10)
        filters = json.loads(response.text)['data']['filters']
        category_filter = next((f for f in filters if f.get('name') == 'Категория'), None)
        if category_filter:
            return [Category(id=i['id'], name=i['name'], level=99) for i in category_filter['items']]
    except Exception as e:
        print(f"[ошибка] {url}\n{e}")
    return []


async def parse_categories(data: list, session: AsyncSession) -> list[Category]:
    categories = []
    stack = [(item, 1) for item in data]
    tasks = []

    while stack:
        item, level = stack.pop()
        cat = Category(
            id=item["id"],
            name=item["name"],
            level=level,
            url=item.get('url', ""),
            shard=item.get('shard', ""),
            query=item.get('query', "")
        )
        categories.append(cat)

        if "childs" in item and isinstance(item["childs"], list):
            for child in item["childs"]:
                stack.append((child, level + 1))

        if item.get("shard") not in ('blackhole', '', None) and item.get("query"):
            tasks.append(fetch_filter_categories(session, item['shard'], item['query']))

    results = await asyncio.gather(*tasks)
    for result in results:
        categories.extend(result)

    return categories


async def load_base_json(session: AsyncSession):
    response = await session.get("https://static-basket-01.wbbasket.ru/vol0/data/main-menu-by-ru-v3.json")
    return json.loads(response.text)


async def main():
    grouped = {}

    async with AsyncSession() as session:
        raw_data = await load_base_json(session)

        for block in raw_data:
            root_name = block["name"]
            cats = await parse_categories([block], session)
            grouped[root_name] = cats

    with ExcelWriter("wildberries_categories.xlsx", engine="openpyxl") as writer:
        for sheet_name, categories in grouped.items():
            df = DataFrame([cat.to_dict() for cat in categories])
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)


if __name__ == "__main__":
    asyncio.run(main())
