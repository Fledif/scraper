import requests
import json

def test_robota():
    url = "https://dracula.robota.ua/?q=getPublishedVacanciesList"
    payload = {
        "operationName": "getPublishedVacanciesList",
        "variables": {
            "pagination": {"count": 20, "page": 0},
            "filter": {}
        },
        "query": "query getPublishedVacanciesList($pagination: PublishedVacanciesPaginationInput!, $filter: PublishedVacanciesFilterInput!) { publishedVacancies(pagination: $pagination, filter: $filter) { totalCount items { id title companyName shortDescription } } }"
    }
    try:
        res = requests.post(url, json=payload, headers={'User-Agent': 'Mozilla/5.0'})
        print("Robota GraphQL:", res.status_code, res.text[:200])
    except Exception as e:
        print("Error:", e)

def test_jooble_api():
    url = "https://ua.jooble.org/api/"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        print("Jooble API:", res.status_code)
    except Exception as e:
        print("Error:", e)

test_robota()
test_jooble_api()
