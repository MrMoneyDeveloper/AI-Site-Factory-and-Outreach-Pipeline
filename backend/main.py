import html
import io
import os
import re
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr


load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True, encoding="utf-8-sig")

APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "compass~crawler-google-places")
APIFY_API_BASE = "https://api.apify.com/v2"
NETLIFY_API_BASE = "https://api.netlify.com/api/v1"
DEFAULT_LOCATION_QUERY = os.getenv("DEFAULT_LOCATION_QUERY", "Durban, South Africa")
SCRAPE_RESULT_LIMIT = int(os.getenv("SCRAPE_RESULT_LIMIT", "10"))


app = FastAPI(title="AI Site Factory Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ai-site-factory-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


INDUSTRY_PRESETS: Dict[str, Dict[str, Any]] = {
    "plumbers": {
        "label": "Plumbers",
        "query": "plumbers",
        "angle": "Emergency repairs, leak detection, drain clearing, and residential plumbing.",
        "services": ["Emergency plumbing", "Leak detection", "Drain and pipe repairs"],
    },
    "electricians": {
        "label": "Electricians",
        "query": "electricians",
        "angle": "Certified electrical work, fault finding, wiring, and safety inspections.",
        "services": ["Electrical repairs", "Wiring upgrades", "Compliance inspections"],
    },
    "hvac": {
        "label": "HVAC",
        "query": "air conditioning repair",
        "angle": "Air conditioning installation, servicing, repairs, and maintenance plans.",
        "services": ["AC installation", "System servicing", "Breakdown repairs"],
    },
    "roofing": {
        "label": "Roofing",
        "query": "roofing contractors",
        "angle": "Roof repairs, waterproofing, inspections, and long-term maintenance.",
        "services": ["Roof repairs", "Waterproofing", "Roof inspections"],
    },
    "landscaping": {
        "label": "Landscaping",
        "query": "landscaping services",
        "angle": "Garden design, maintenance, cleanups, and outdoor improvements.",
        "services": ["Garden maintenance", "Landscape design", "Outdoor cleanups"],
    },
    "dentists": {
        "label": "Dentists",
        "query": "dentists",
        "angle": "Family dental care, checkups, cosmetic dentistry, and emergency appointments.",
        "services": ["Dental checkups", "Cosmetic dentistry", "Emergency dental care"],
    },
    "restaurants": {
        "label": "Restaurants",
        "query": "restaurants",
        "angle": "Local dining, bookings, menus, events, and customer discovery.",
        "services": ["Table bookings", "Menu highlights", "Private events"],
    },
    "mechanics": {
        "label": "Mechanics",
        "query": "auto mechanics",
        "angle": "Vehicle servicing, diagnostics, repairs, and maintenance reminders.",
        "services": ["Vehicle servicing", "Diagnostics", "Mechanical repairs"],
    },
}


class LeadInput(BaseModel):
    businessName: str
    email: EmailStr
    category: str
    location: Optional[str] = "Not provided"
    notes: Optional[str] = "No additional notes provided."


class CleanedLead(BaseModel):
    businessName: str
    email: EmailStr
    category: str
    location: str
    cleanSummary: str
    status: str
    readyForAI: str


class ServiceBlock(BaseModel):
    title: str
    description: str


class ContentPacket(BaseModel):
    headline: str
    summary: str
    services: List[ServiceBlock]
    cta: str
    tone: str
    brandNotes: str
    generatedAt: str  

class IndustryPreset(BaseModel):
    id: str
    label: str
    apifyActorId: str
    resultLimit: int
    inputTemplate: Dict[str, Any]
    siteAngle: str


class BusinessLead(BaseModel):
    id: str
    sourceIndustryId: str
    industryLabel: str
    businessName: str
    category: str
    address: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    reviewsCount: Optional[int] = None
    googleMapsUrl: Optional[str] = None
    notes: Optional[str] = None
    source: str = "Apify Google Maps Scraper"


class ScrapeRequest(BaseModel):
    industryIds: List[str]
    locationQuery: Optional[str] = None


class ScrapeResponse(BaseModel):
    locationQuery: str
    resultLimitPerIndustry: int
    leads: List[BusinessLead]
    failures: List[Dict[str, str]]
    generatedAt: str


class DeployRequest(BaseModel):
    leads: List[BusinessLead]


class DeploymentResult(BaseModel):
    leadId: str
    businessName: str
    status: str
    siteName: Optional[str] = None
    deployUrl: Optional[str] = None
    adminUrl: Optional[str] = None
    prompt: Optional[str] = None
    error: Optional[str] = None
    action: Optional[str] = None


class DeployResponse(BaseModel):
    deployments: List[DeploymentResult]
    generatedAt: str


def api_error(status_code: int, message: str, action: str, details: Optional[Any] = None) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "action": action,
            "details": details,
        },
    )


def get_required_env(name: str, service_name: str) -> str:
    value = os.getenv(name)
    if not value:
        api_error(
            500,
            f"{service_name} token is missing.",
            f"Add {name} to the root .env file and restart the backend.",
        )
    return value


def build_apify_input(industry_id: str, location_query: str) -> Dict[str, Any]:
    preset = INDUSTRY_PRESETS[industry_id]
    return {
        "searchStringsArray": [preset["query"]],
        "locationQuery": location_query,
        "maxCrawledPlacesPerSearch": SCRAPE_RESULT_LIMIT,
        "language": "en",
        "scrapeSocialMediaProfiles": {
            "facebooks": False,
            "instagrams": False,
            "youtubes": False,
            "tiktoks": False,
            "twitters": False,
        },
        "maximumLeadsEnrichmentRecords": 0,
    }


def make_slug(value: str, max_length: int = 44) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or "site")[:max_length].strip("-")


def first_value(*values: Any) -> Optional[Any]:
    for value in values:
        if isinstance(value, list) and value:
            return value[0]
        if value not in (None, "", []):
            return value
    return None


def normalize_email(item: Dict[str, Any]) -> Optional[str]:
    email = first_value(item.get("email"), item.get("emails"))
    if isinstance(email, dict):
        email = first_value(email.get("email"), email.get("value"))
    return str(email) if email else None


def normalize_category(item: Dict[str, Any], fallback: str) -> str:
    category = first_value(item.get("categoryName"), item.get("category"), item.get("categories"))
    if isinstance(category, dict):
        category = first_value(category.get("name"), category.get("title"))
    return str(category) if category else fallback


def normalize_website(value: Optional[Any]) -> Optional[str]:
    if not value:
        return None
    website = str(value).strip()
    if website.startswith(("http://", "https://")):
        return website
    return f"https://{website}"


def safe_float(value: Optional[Any]) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def safe_int(value: Optional[Any]) -> Optional[int]:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalize_lead(item: Dict[str, Any], industry_id: str, index: int, location_query: str) -> Optional[BusinessLead]:
    preset = INDUSTRY_PRESETS[industry_id]
    name = first_value(item.get("title"), item.get("name"), item.get("businessName"))
    if not name:
        return None

    website = normalize_website(first_value(item.get("website"), item.get("websiteUrl")))
    phone = first_value(item.get("phone"), item.get("phoneUnformatted"), item.get("telephone"))
    address = first_value(item.get("address"), item.get("street"), item.get("fullAddress"))
    maps_url = first_value(item.get("url"), item.get("googleMapsUrl"), item.get("placeUrl"))
    rating = first_value(item.get("totalScore"), item.get("rating"), item.get("stars"))
    reviews_count = first_value(item.get("reviewsCount"), item.get("reviewCount"))

    notes = [
        preset["angle"],
        f"Source location: {location_query}.",
    ]
    if rating:
        notes.append(f"Rating: {rating}.")
    if reviews_count:
        notes.append(f"Reviews: {reviews_count}.")

    lead_id = f"{industry_id}-{index + 1}-{make_slug(str(name), 30)}"
    return BusinessLead(
        id=lead_id,
        sourceIndustryId=industry_id,
        industryLabel=preset["label"],
        businessName=str(name),
        category=normalize_category(item, preset["label"]),
        address=str(address) if address else None,
        location=location_query,
        phone=str(phone) if phone else None,
        email=normalize_email(item),
        website=website,
        rating=safe_float(rating),
        reviewsCount=safe_int(reviews_count),
        googleMapsUrl=str(maps_url) if maps_url else None,
        notes=" ".join(notes),
    )


def run_apify_scrape(industry_id: str, location_query: str) -> List[BusinessLead]:
    token = get_required_env("APIFY_API_TOKEN", "Apify")
    actor_id = APIFY_ACTOR_ID.replace("/", "~")
    endpoint = f"{APIFY_API_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
    response = requests.post(
        endpoint,
        params={
            "format": "json",
            "clean": "true",
            "timeout": 180,
            "maxItems": SCRAPE_RESULT_LIMIT,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=build_apify_input(industry_id, location_query),
        timeout=240,
    )

    if response.status_code >= 400:
        api_error(
            response.status_code,
            f"Apify scrape failed for {INDUSTRY_PRESETS[industry_id]['label']}.",
            "Check the Apify token, actor availability, account credits, and the selected location.",
            response.text[:700],
        )

    items = response.json()
    if not isinstance(items, list):
        api_error(
            502,
            f"Apify returned an unexpected response for {INDUSTRY_PRESETS[industry_id]['label']}.",
            "Open the Apify run log for this actor and confirm the output dataset is JSON.",
            items,
        )

    leads: List[BusinessLead] = []
    for item in items:
        if len(leads) >= SCRAPE_RESULT_LIMIT:
            break
        if isinstance(item, dict):
            lead = normalize_lead(item, industry_id, len(leads), location_query)
            if lead:
                leads.append(lead)
    return leads


def escape(value: Optional[Any]) -> str:
    return html.escape(str(value)) if value not in (None, "") else ""


def build_site_prompt(lead: BusinessLead) -> str:
    preset = INDUSTRY_PRESETS.get(lead.sourceIndustryId, {})
    services = ", ".join(preset.get("services", [lead.category]))
    return (
        f"Generate a conversion-focused landing page for {lead.businessName}, "
        f"a {lead.category} business in {lead.location or lead.address or 'the local area'}. "
        f"Use the business context: {lead.notes or preset.get('angle', '')}. "
        f"Prioritize these service sections: {services}. "
        f"Use these contact details exactly where available: phone={lead.phone or 'not provided'}, "
        f"email={lead.email or 'not provided'}, website={lead.website or 'not provided'}, "
        f"address={lead.address or 'not provided'}."
    )


def render_landing_page(lead: BusinessLead, prompt: str) -> str:
    preset = INDUSTRY_PRESETS.get(lead.sourceIndustryId, {})
    services = preset.get("services", [lead.category, "Fast response", "Local support"])
    service_cards = "\n".join(
        f"""
        <article class="service">
          <span>{index:02d}</span>
          <h3>{escape(service)}</h3>
          <p>Practical support from a local team with clear communication and reliable follow-through.</p>
        </article>
        """
        for index, service in enumerate(services, start=1)
    )

    contact_lines = [
        ("Phone", lead.phone),
        ("Email", lead.email),
        ("Website", lead.website),
        ("Address", lead.address),
    ]
    contact_markup = "\n".join(
        f"<p><strong>{label}</strong><br>{escape(value)}</p>"
        for label, value in contact_lines
        if value
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(lead.businessName)} | {escape(lead.category)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: #172033;
      background: #f4f1ea;
    }}
    .hero {{
      min-height: 76vh;
      display: grid;
      align-items: end;
      padding: 56px;
      color: white;
      background:
        linear-gradient(120deg, rgba(17, 24, 39, 0.94), rgba(22, 101, 52, 0.72)),
        url("https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1800&q=80") center/cover;
    }}
    .hero-inner {{ max-width: 860px; }}
    .eyebrow {{ text-transform: uppercase; font-weight: 800; font-size: 13px; letter-spacing: 0; }}
    h1 {{ font-size: clamp(38px, 7vw, 82px); line-height: 0.95; margin: 14px 0; letter-spacing: 0; }}
    .hero p {{ font-size: 20px; line-height: 1.55; max-width: 720px; }}
    .cta-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin-top: 28px; }}
    .cta {{
      display: inline-flex;
      color: #172033;
      background: #f8d66d;
      text-decoration: none;
      font-weight: 800;
      padding: 14px 18px;
      border-radius: 6px;
    }}
    main {{ padding: 40px 56px 64px; }}
    .section-title {{ max-width: 760px; margin-bottom: 24px; }}
    .section-title h2 {{ font-size: 36px; margin-bottom: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }}
    .service, .contact {{
      background: white;
      border: 1px solid #e4ded0;
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 10px 28px rgba(23, 32, 51, 0.08);
    }}
    .service span {{ color: #166534; font-weight: 900; }}
    .contact {{ margin-top: 28px; display: grid; grid-template-columns: 1.2fr 1fr; gap: 22px; }}
    .prompt {{ color: #5c6474; font-size: 13px; line-height: 1.5; }}
    @media (max-width: 760px) {{
      .hero {{ padding: 34px 22px; min-height: 72vh; }}
      main {{ padding: 30px 22px; }}
      .grid, .contact {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <section class="hero">
    <div class="hero-inner">
      <div class="eyebrow">{escape(lead.industryLabel)} in {escape(lead.location or "your area")}</div>
      <h1>{escape(lead.businessName)}</h1>
      <p>{escape(preset.get("angle", "Local services with clear communication and reliable delivery."))}</p>
      <div class="cta-row">
        {f'<a class="cta" href="tel:{escape(lead.phone)}">Call {escape(lead.phone)}</a>' if lead.phone else ''}
        {f'<a class="cta" href="{escape(lead.website)}">Visit website</a>' if lead.website else ''}
      </div>
    </div>
  </section>
  <main>
    <section>
      <div class="section-title">
        <h2>Services built around local customers</h2>
        <p>{escape(lead.notes)}</p>
      </div>
      <div class="grid">{service_cards}</div>
    </section>
    <section class="contact">
      <div>
        <h2>Contact {escape(lead.businessName)}</h2>
        {contact_markup or "<p>Contact details were not available in the scraped lead record.</p>"}
      </div>
      <div class="prompt">
        <strong>Generation context</strong>
        <p>{escape(prompt)}</p>
      </div>
    </section>
  </main>
</body>
</html>"""


def zip_site(html_content: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", html_content)
    buffer.seek(0)
    return buffer.read()


def poll_deploy(token: str, deploy_id: str, max_wait_seconds: int = 20) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + max_wait_seconds
    last_response: Dict[str, Any] = {}
    while time.time() < deadline:
        response = requests.get(
            f"{NETLIFY_API_BASE}/deploys/{deploy_id}",
            headers=headers,
            timeout=20,
        )
        if response.status_code >= 400:
            return last_response
        last_response = response.json()
        if last_response.get("state") in {"ready", "error"}:
            return last_response
        time.sleep(2)
    return last_response


def deploy_to_netlify(lead: BusinessLead) -> DeploymentResult:
    token = get_required_env("NETLIFY_API_TOKEN", "Netlify")
    prompt = build_site_prompt(lead)
    site_html = render_landing_page(lead, prompt)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    site_name = f"aifs-{make_slug(lead.businessName, 28)}-{timestamp}"
    auth_headers = {"Authorization": f"Bearer {token}"}

    site_response = requests.post(
        f"{NETLIFY_API_BASE}/sites",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={
            "name": site_name,
            "processing_settings": {"html": {"pretty_urls": True}},
        },
        timeout=30,
    )
    if site_response.status_code >= 400:
        return DeploymentResult(
            leadId=lead.id,
            businessName=lead.businessName,
            status="failed",
            siteName=site_name,
            prompt=prompt,
            error="Netlify site creation failed.",
            action="Check the Netlify token, account permissions, and whether the generated site name is available.",
        )

    site_data = site_response.json()
    site_id = site_data.get("id") or site_data.get("site_id") or site_data.get("name")
    if not site_id:
        return DeploymentResult(
            leadId=lead.id,
            businessName=lead.businessName,
            status="failed",
            siteName=site_name,
            prompt=prompt,
            error="Netlify did not return a site ID.",
            action="Open the Netlify account activity log and confirm API site creation is enabled.",
        )

    deploy_response = requests.post(
        f"{NETLIFY_API_BASE}/sites/{site_id}/deploys",
        headers={**auth_headers, "Content-Type": "application/zip"},
        data=zip_site(site_html),
        timeout=60,
    )
    if deploy_response.status_code >= 400:
        return DeploymentResult(
            leadId=lead.id,
            businessName=lead.businessName,
            status="failed",
            siteName=site_name,
            prompt=prompt,
            adminUrl=site_data.get("admin_url"),
            error="Netlify deploy upload failed.",
            action="Check deploy permissions for this token and retry with a smaller generated site package.",
        )

    deploy_data = deploy_response.json()
    final_data = deploy_data
    if deploy_data.get("id"):
        final_data = poll_deploy(token, deploy_data["id"]) or deploy_data

    state = final_data.get("state") or deploy_data.get("state") or "uploaded"
    status = "deployed" if state == "ready" else "processing"
    deploy_url = (
        final_data.get("deploy_ssl_url")
        or deploy_data.get("deploy_ssl_url")
        or site_data.get("ssl_url")
        or site_data.get("url")
    )

    return DeploymentResult(
        leadId=lead.id,
        businessName=lead.businessName,
        status=status,
        siteName=site_name,
        deployUrl=deploy_url,
        adminUrl=site_data.get("admin_url"),
        prompt=prompt,
    )


@app.get("/")
def health_check():
    return {
        "message": "AI Site Factory Backend is running",
        "status": "online",
    }


@app.get("/api/config/status")
def config_status():
    return {
        "apifyConfigured": bool(os.getenv("APIFY_API_TOKEN")),
        "netlifyConfigured": bool(os.getenv("NETLIFY_API_TOKEN")),
        "defaultLocationQuery": DEFAULT_LOCATION_QUERY,
        "resultLimitPerIndustry": SCRAPE_RESULT_LIMIT,
        "apifyActorId": APIFY_ACTOR_ID,
    }


@app.get("/api/industries", response_model=List[IndustryPreset])
def get_industries():
    return [
        IndustryPreset(
            id=industry_id,
            label=preset["label"],
            apifyActorId=APIFY_ACTOR_ID,
            resultLimit=SCRAPE_RESULT_LIMIT,
            inputTemplate=build_apify_input(industry_id, DEFAULT_LOCATION_QUERY),
            siteAngle=preset["angle"],
        )
        for industry_id, preset in INDUSTRY_PRESETS.items()
    ]


@app.post("/api/scrape", response_model=ScrapeResponse)
def scrape_businesses(request: ScrapeRequest):
    if not request.industryIds:
        api_error(
            400,
            "No industries were selected.",
            "Select at least one industry preset before running the Apify scrape.",
        )

    unknown_ids = [industry_id for industry_id in request.industryIds if industry_id not in INDUSTRY_PRESETS]
    if unknown_ids:
        api_error(
            400,
            "One or more selected industry presets are not configured.",
            "Refresh the page and choose from the available industry list.",
            unknown_ids,
        )

    location_query = (request.locationQuery or DEFAULT_LOCATION_QUERY).strip()
    all_leads: List[BusinessLead] = []
    failures: List[Dict[str, str]] = []

    for industry_id in request.industryIds:
        try:
            all_leads.extend(run_apify_scrape(industry_id, location_query))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            failures.append(
                {
                    "industryId": industry_id,
                    "message": str(detail.get("message", "Scrape failed.")),
                    "action": str(detail.get("action", "Check the backend logs.")),
                }
            )

    if not all_leads and failures:
        api_error(
            502,
            "No business leads were returned from Apify.",
            "Check the listed scrape failures, then retry with fewer industries or a more specific location.",
            failures,
        )

    return ScrapeResponse(
        locationQuery=location_query,
        resultLimitPerIndustry=SCRAPE_RESULT_LIMIT,
        leads=all_leads,
        failures=failures,
        generatedAt=datetime.now().isoformat(),
    )


@app.post("/api/deploy", response_model=DeployResponse)
def deploy_landing_pages(request: DeployRequest):
    if not request.leads:
        api_error(
            400,
            "No businesses were selected for deployment.",
            "Select at least one scraped business before submitting to the Netlify deploy step.",
        )

    deployments = [deploy_to_netlify(lead) for lead in request.leads]
    return DeployResponse(
        deployments=deployments,
        generatedAt=datetime.now().isoformat(),
    )


@app.post("/api/leads/clean", response_model=CleanedLead)
def clean_lead(lead: LeadInput):
    return CleanedLead(
        businessName=lead.businessName.strip(),
        email=lead.email.lower(),
        category=lead.category.strip(),
        location=lead.location.strip() if lead.location else "Not provided",
        cleanSummary=lead.notes.strip()
        if lead.notes
        else "No additional notes provided.",
        status="CLEAN",
        readyForAI="YES",
    )


@app.post("/api/content/generate", response_model=ContentPacket)
def generate_content(cleaned_lead: CleanedLead):
    return ContentPacket(
        headline=f"{cleaned_lead.businessName} - {cleaned_lead.category} Services in {cleaned_lead.location}",
        summary=(
            f"{cleaned_lead.businessName} provides reliable "
            f"{cleaned_lead.category.lower()} services in {cleaned_lead.location}. "
            f"{cleaned_lead.cleanSummary}"
        ),
        services=[
            ServiceBlock(
                title=f"Professional {cleaned_lead.category} Support",
                description=f"Reliable {cleaned_lead.category.lower()} support tailored to customer needs.",
            ),
            ServiceBlock(
                title="Customer-Focused Service",
                description="Clear communication, practical assistance, and dependable service delivery.",
            ),
            ServiceBlock(
                title="Local Business Support",
                description=f"Serving customers in and around {cleaned_lead.location}.",
            ),
        ],
        cta=f"Contact {cleaned_lead.businessName} today to learn more.",
        tone="Professional and clear",
        brandNotes="Generated from cleaned lead data. No unsupported claims added.",
        generatedAt=datetime.now().isoformat(),
    )
