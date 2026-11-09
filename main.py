"""TKP Generator App — FastAPI + Bitrix24 + Playwright"""
import os
import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright

import bx24

app = FastAPI(title="Генератор ТКП Альтегрити")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ============ CACHE ============

cache = {}


def refresh_cache():
    """Load all data from Bitrix24 into cache"""
    cache["models"] = bx24.get_models()
    cache["options"] = bx24.get_options()
    cache["options_by_section"] = bx24.get_options_by_section()
    cache["functions"] = bx24.get_functions()
    cache["functions_by_category"] = bx24.get_functions_by_category()
    cache["components"] = bx24.get_components()
    cache["companies"] = bx24.get_companies()
    cache["managers"] = bx24.get_managers()
    cache["updated_at"] = datetime.now()


@app.on_event("startup")
async def startup():
    refresh_cache()


# ============ PAGES ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve client app"""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/api/refresh")
async def api_refresh():
    refresh_cache()
    return {"status": "ok", "updated_at": cache.get("updated_at")}


@app.get("/api/contacts/{company_id}")
async def api_contacts(company_id: int):
    return bx24.get_company_contacts(company_id)


# ============ GENERATE TKP ============

@app.post("/generate")
async def generate_tkp(
    model_id: int = Form(...),
    client_company: str = Form(""),
    client_contact: str = Form(""),
    client_phone: str = Form(""),
    manager_name: str = Form(""),
    manager_position: str = Form(""),
    manager_email: str = Form(""),
    selected_options: list[str] = Form(default=[]),
    power_kw: str = Form("20"),
    source: str = Form("Raycus"),
):
    """Generate TKP PDF from form data"""
    
    # Get model details
    model = None
    for m in cache.get("models", []):
        if str(m["id"]) == str(model_id):
            model = m
            break
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Get selected options with prices
    opts = []
    total_options = 0
    for opt_id in selected_options:
        for o in cache.get("options", []):
            if str(o["id"]) == opt_id:
                opts.append(o)
                total_options += o["price"]
                break
    
    # Calculate totals
    base_price = model["price"]
    vat_rate = 0.22
    total_without_vat = base_price + total_options
    vat_amount = total_without_vat * vat_rate
    total_with_vat = total_without_vat + vat_amount
    
    # Generate document number
    doc_num = f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    
    # Build context for template
    context = {
        "doc_num": doc_num,
        "doc_date": datetime.now().strftime("%d.%m.%Y"),
        "model_name": model["name"],
        "model_full": f"{model['name']} {power_kw} кВт {source}",
        "power_kw": power_kw,
        "source": source,
        "client_company": client_company,
        "client_contact": client_contact,
        "client_phone": client_phone,
        "manager_name": manager_name,
        "manager_position": manager_position,
        "manager_email": manager_email,
        "base_price": base_price,
        "options": opts,
        "total_options": total_options,
        "total_without_vat": total_without_vat,
        "vat_amount": vat_amount,
        "total_with_vat": total_with_vat,
        "functions_by_category": cache.get("functions_by_category", {}),
        "components": cache.get("components", []),
    }
    
    # Render HTML
    template = templates.get_template("tkp_template.html")
    html_content = template.render(request=None, **context)
    
    # Save HTML
    html_path = OUTPUT_DIR / f"TKP_{doc_num}.html"
    html_path.write_text(html_content, encoding="utf-8")
    
    # Render PDF
    pdf_path = OUTPUT_DIR / f"TKP_{doc_num}.pdf"
    await render_pdf(str(html_path), str(pdf_path))
    
    return {
        "status": "ok",
        "doc_num": doc_num,
        "html_url": f"/download/{html_path.name}",
        "pdf_url": f"/download/{pdf_path.name}",
    }


@app.post("/generate/pdf")
async def generate_pdf(
    model_id: int = Form(...),
    client_company: str = Form(""),
    client_contact: str = Form(""),
    client_phone: str = Form(""),
    manager_name: str = Form(""),
    manager_position: str = Form(""),
    manager_email: str = Form(""),
    selected_options: list[str] = Form(default=[]),
    power_kw: str = Form("20"),
    source: str = Form("Raycus"),
):
    """Generate TKP PDF and return as file download"""
    result = await generate_tkp(
        model_id=model_id,
        client_company=client_company,
        client_contact=client_contact,
        client_phone=client_phone,
        manager_name=manager_name,
        manager_position=manager_position,
        manager_email=manager_email,
        selected_options=selected_options,
        power_kw=power_kw,
        source=source,
    )
    pdf_path = OUTPUT_DIR / f"TKP_{result['doc_num']}.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"TKP_{result['doc_num']}.pdf"
    )


@app.get("/download/{filename}")
async def download(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404)
    media_type = "application/pdf" if filename.endswith(".pdf") else "text/html"
    return FileResponse(path, media_type=media_type, filename=filename)


# ============ PDF RENDERER ============

async def render_pdf(html_path: str, pdf_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file://{html_path}")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(500)
        await page.pdf(
            path=pdf_path,
            format="A4",
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            print_background=True,
        )
        await browser.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
