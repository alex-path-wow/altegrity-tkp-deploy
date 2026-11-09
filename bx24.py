"""Bitrix24 REST API client for TKP Generator"""
import requests
from typing import Any

WH = "https://altegrity.bitrix24.ru/rest/1/6wde7t63hxqv5jhb"


def api(method: str, data: dict | None = None) -> dict:
    r = requests.post(f"{WH}/{method}", json=data or {}, timeout=30)
    return r.json()


# ============ PRICE HELPERS ============

def get_product_prices(product_id: int) -> list[dict]:
    """Get all prices for a product from catalog.price.list"""
    resp = api("catalog.price.list", {
        "filter": {"productId": product_id},
        "select": ["id", "productId", "priceTypeId", "price", "currency"]
    })
    return resp.get("result", {}).get("prices", [])


def get_product_price(product_id: int, currency: str = "RUB") -> float:
    """Get client price for a product in specified currency (from price types)"""
    prices = get_product_prices(product_id)
    for p in prices:
        if p.get("currency") == currency:
            return float(p.get("price") or 0)
    # Fallback: return first available price
    if prices:
        return float(prices[0].get("price") or 0)
    return 0


def get_product_purchase_price(product_id: int) -> tuple[float, str]:
    """Get purchase price (purchasingPrice) and currency from catalog.product
    
    In Bitrix24, 'Закупочная цена' is stored as purchasingPrice/purchasingCurrency
    fields in catalog.product, NOT as a separate price type.
    Returns: (price, currency)
    """
    resp = api("catalog.product.list", {
        "filter": {"id": product_id, "iblockId": 15},
        "select": ["id", "iblockId", "purchasingPrice", "purchasingCurrency"]
    })
    products = resp.get("result", {}).get("products", [])
    if products:
        p = products[0]
        price = float(p.get("purchasingPrice") or 0)
        currency = p.get("purchasingCurrency", "CNY")
        return price, currency
    return 0, "CNY"


def get_product_image(product_id: int) -> str | None:
    """Get image URL from PROPERTY_45 (Картинка)"""
    resp = api("crm.product.get", {"id": product_id})
    item = resp.get("result", {})
    prop = item.get("PROPERTY_45")
    if prop and isinstance(prop, list) and len(prop) > 0:
        val = prop[0].get("value", {})
        return val.get("showUrl") or val.get("downloadUrl")
    return None


# ============ PRODUCTS / MODELS ============

def get_models() -> list[dict]:
    """Get laser cutting machine models from section 6055 (Раскрой листа)"""
    resp = api("crm.product.list", {
        "filter": {"SECTION_ID": 6055},
        "select": ["ID", "NAME", "PRICE", "CURRENCY_ID", "DESCRIPTION", "PROPERTY_45"],
        "order": {"NAME": "ASC"},
        "limit": 50
    })
    items = resp.get("result", [])
    models = []
    for item in items:
        name = item.get("NAME", "")
        # Skip options that are in the models section
        if any(x in name for x in ["Bevel", "Zoom", "MixGas", "BlueEye", "Raster"]):
            continue
        pid = int(item["ID"])
        # Get client price from catalog.price.list (RUB)
        client_price = get_product_price(pid, "RUB")
        # Get purchase price from catalog.product.purchasingPrice (CNY)
        purchase_price, purchase_currency = get_product_purchase_price(pid)
        # Get image
        image = None
        prop = item.get("PROPERTY_45")
        if prop and isinstance(prop, list) and len(prop) > 0:
            val = prop[0].get("value", {})
            image = val.get("showUrl") or val.get("downloadUrl")
        models.append({
            "id": pid,
            "name": name,
            "price": client_price,
            "currency": "RUB",
            "purchase_price": purchase_price,
            "purchase_currency": purchase_currency,
            "description": item.get("DESCRIPTION", ""),
            "image": image
        })
    return models


def get_model_by_id(model_id: int) -> dict | None:
    """Get model by ID"""
    for model in get_models():
        if str(model["id"]) == str(model_id):
            return model
    return None


def get_model_price(model_id: int) -> float:
    """Get product price by ID in RUB"""
    return get_product_price(model_id, "RUB")


# ============ OPTIONS ============

OPTION_SECTIONS = {
    7089: "Лазер листовой",
    7091: "Труборез",
    7093: "Листогиб",
    7095: "Общие"
}


def get_options() -> list[dict]:
    """Get all options from subsections of 7087.
    
    Returns purchase price (purchasingPrice) in original currency (CNY).
    Client-facing prices come from catalog.price.list (RUB/CNY).
    """
    options = []
    for sec_id, sec_name in OPTION_SECTIONS.items():
        resp = api("crm.product.list", {
            "filter": {"SECTION_ID": sec_id, "ACTIVE": "Y"},
            "select": ["ID", "NAME", "PRICE", "CURRENCY_ID", "DESCRIPTION"],
            "limit": 50
        })
        for item in resp.get("result", []):
            pid = int(item["ID"])
            # Get purchase price from catalog.product.purchasingPrice
            purchase_price, purchase_currency = get_product_purchase_price(pid)
            # Get client price from catalog.price.list (fallback to PRICE field)
            client_price = get_product_price(pid, "RUB") or get_product_price(pid, "CNY")
            options.append({
                "id": pid,
                "name": item["NAME"],
                "purchase_price": purchase_price,
                "purchase_currency": purchase_currency,
                "client_price": client_price,
                "client_currency": "RUB" if client_price > 0 else purchase_currency,
                "section_id": sec_id,
                "section_name": sec_name,
                "description": item.get("DESCRIPTION", "")
            })
    return options


def get_options_by_section() -> dict[str, list[dict]]:
    """Get options grouped by section"""
    result = {name: [] for name in OPTION_SECTIONS.values()}
    for opt in get_options():
        result[opt["section_name"]].append(opt)
    return result


# ============ FUNCTIONS ============

FUNCTION_CATEGORY_MAP = {
    10369: "Безопасность",
    10371: "Оптика и лазер",
    10373: "Автоматика",
    10375: "Удобство эксплуатации",
    10377: "Программное обеспечение",
}


def get_functions() -> list[dict]:
    """Get functions from smart process entityTypeId 1164"""
    resp = api("crm.item.list", {
        "entityTypeId": 1164,
        "select": ["id", "title", "ufCrm61ShortDesc", "ufCrm61FullDesc", "ufCrm61Category", "ufCrm61Series"]
    })
    items = resp.get("result", {}).get("items", [])
    functions = []
    for item in items:
        cat_id = item.get("ufCrm61Category")
        cat_name = FUNCTION_CATEGORY_MAP.get(cat_id, "Удобство")
        series_ids = item.get("ufCrm61Series") or []
        functions.append({
            "id": item["id"],
            "name": item.get("title", ""),
            "description": item.get("ufCrm61ShortDesc", ""),
            "full_description": item.get("ufCrm61FullDesc", ""),
            "category": cat_name,
            "category_id": cat_id,
            "series_ids": series_ids,
        })
    return functions


def get_functions_by_category(model_id: str | None = None) -> dict[str, list[dict]]:
    """Get functions grouped by category, optionally filtered by model"""
    result = {}
    for fn in get_functions():
        cat = fn["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(fn)
    return result


# ============ COMPONENTS ============

def get_components() -> list[dict]:
    """Get key components from smart process entityTypeId 1176"""
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


# ============ QUOTE DATA ============

def get_quote_data(quote_id: int) -> dict:
    """Get full quote data including client, contact, manager, products"""
    # Get quote
    resp = api("crm.quote.get", {"id": quote_id})
    quote = resp.get("result", {})
    
    # Get product rows
    product_rows = []
    resp_rows = api("crm.quote.productrows.get", {"id": quote_id})
    rows = resp_rows.get("result", [])
    for row in rows:
        product_rows.append({
            "product_id": row.get("PRODUCT_ID"),
            "product_name": row.get("PRODUCT_NAME"),
            "quantity": row.get("QUANTITY"),
            "price": row.get("PRICE"),
            "sum": row.get("SUM"),
        })
    
    # Get company
    company = {}
    company_id = quote.get("COMPANY_ID")
    if company_id:
        resp_comp = api("crm.company.get", {"id": company_id})
        c = resp_comp.get("result", {})
        company = {
            "id": company_id,
            "name": c.get("TITLE", ""),
            "phone": c.get("PHONE", [{}])[0].get("VALUE", "") if c.get("PHONE") else "",
        }
    
    # Get contact
    contact = {}
    contact_id = quote.get("CONTACT_ID")
    if contact_id:
        resp_cont = api("crm.contact.get", {"id": contact_id})
        c = resp_cont.get("result", {})
        contact = {
            "id": contact_id,
            "name": f"{c.get('NAME', '')} {c.get('LAST_NAME', '')}".strip(),
            "phone": c.get("PHONE", [{}])[0].get("VALUE", "") if c.get("PHONE") else "",
            "post": c.get("POST", ""),
        }
    
    # Get manager
    manager = {}
    assigned_id = quote.get("ASSIGNED_BY_ID")
    if assigned_id:
        resp_user = api("user.get", {"filter": {"ID": assigned_id}})
        users = resp_user.get("result", [])
        if users:
            u = users[0]
            manager = {
                "id": assigned_id,
                "name": f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip(),
                "email": u.get("EMAIL", ""),
                "position": u.get("WORK_POSITION", ""),
            }
    
    return {
        "quote_id": quote_id,
        "opportunity": float(quote.get("OPPORTUNITY") or 0),
        "currency": quote.get("CURRENCY_ID", "RUB"),
        "company": company,
        "contact": contact,
        "manager": manager,
        "product_rows": product_rows,
    }


# ============ COMPANIES / MANAGERS ============

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
