"""Bitrix24 REST API client for TKP Generator"""
import requests
from typing import Any

WH = "https://altegrity.bitrix24.ru/rest/1/6wde7t63hxqv5jhb"


def api(method: str, data: dict | None = None) -> dict:
    r = requests.post(f"{WH}/{method}", json=data or {}, timeout=30)
    return r.json()


# ============ PRODUCTS / MODELS ============

def get_models() -> list[dict]:
    """Get laser cutting machine models from section 6055 (Раскрой листа)"""
    resp = api("crm.product.list", {
        "filter": {"SECTION_ID": 6055},
        "select": ["ID", "NAME", "PRICE", "DESCRIPTION"],
        "order": {"NAME": "ASC"},
        "limit": 50
    })
    items = resp.get("result", [])
    models = []
    for item in items:
        name = item.get("NAME", "")
        if any(x in name for x in ["Bevel", "Zoom", "MixGas", "BlueEye", "Raster"]):
            continue
        models.append({
            "id": item["ID"],
            "name": name,
            "price": float(item["PRICE"]) if item.get("PRICE") else 0,
            "description": item.get("DESCRIPTION", "")
        })
    return models


OPTION_SECTIONS = {
    7089: "Лазер листовой",
    7091: "Труборез",
    7093: "Листогиб",
    7095: "Общие"
}


def get_options() -> list[dict]:
    options = []
    for sec_id, sec_name in OPTION_SECTIONS.items():
        resp = api("crm.product.list", {
            "filter": {"SECTION_ID": sec_id},
            "select": ["ID", "NAME", "PRICE", "DESCRIPTION"],
            "limit": 50
        })
        for item in resp.get("result", []):
            options.append({
                "id": item["ID"],
                "name": item["NAME"],
                "price": float(item["PRICE"]) if item.get("PRICE") else 0,
                "section_id": sec_id,
                "section_name": sec_name,
                "description": item.get("DESCRIPTION", "")
            })
    return options


def get_options_by_section() -> dict[str, list[dict]]:
    result = {name: [] for name in OPTION_SECTIONS.values()}
    for opt in get_options():
        result[opt["section_name"]].append(opt)
    return result


FUNCTION_CATEGORY_MAP = {
    10369: "Безопасность",
    10371: "Оптика и лазер",
    10373: "Автоматика",
    10375: "Удобство эксплуатации",
    10377: "Программное обеспечение",
}


def get_functions() -> list[dict]:
    resp = api("crm.item.list", {
        "entityTypeId": 1164,
        "select": ["id", "title", "ufCrm61ShortDesc", "ufCrm61FullDesc", "ufCrm61Category", "ufCrm61Series"]
    })
    items = resp.get("result", {}).get("items", [])
    functions = []
    for item in items:
        cat_id = item.get("ufCrm61Category")
        cat_name = FUNCTION_CATEGORY_MAP.get(cat_id, "Удобство")
        functions.append({
            "id": item["id"],
            "name": item.get("title", ""),
            "description": item.get("ufCrm61ShortDesc", ""),
            "full_description": item.get("ufCrm61FullDesc", ""),
            "category": cat_name,
            "category_id": cat_id,
        })
    return functions


def get_functions_by_category() -> dict[str, list[dict]]:
    result = {}
    for fn in get_functions():
        cat = fn["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(fn)
    return result


def get_components() -> list[dict]:
    resp = api("crm.item.list", {
        "entityTypeId": 1176,
        "select": ["id", "title", "ufCrm67_1794089101"]
    })
    items = resp.get("result", {}).get("items", [])
    return [{
        "id": item["id"],
        "name": item.get("title", ""),
        "country": item.get("ufCrm67_1794089101", "")
    } for item in items]


def get_companies() -> list[dict]:
    resp = api("crm.company.list", {
        "select": ["ID", "TITLE", "PHONE", "EMAIL"],
        "order": {"TITLE": "ASC"},
        "limit": 100
    })
    return resp.get("result", [])


def get_company_contacts(company_id: int) -> list[dict]:
    resp = api("crm.contact.list", {
        "filter": {"COMPANY_ID": company_id},
        "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "POST"],
        "limit": 20
    })
    return resp.get("result", [])


def get_managers() -> list[dict]:
    resp = api("user.get", {
        "filter": {"ACTIVE": "Y"},
        "select": ["ID", "NAME", "LAST_NAME", "EMAIL", "WORK_POSITION"],
        "limit": 50
    })
    return resp.get("result", [])
