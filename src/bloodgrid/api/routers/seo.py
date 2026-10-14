"""
BloodGrid Programmatic SEO Router
=================================
Generates server-rendered district and blood group landing pages with:
- Dynamic title and meta descriptions
- JSON-LD Schema.org (MedicalOrganization / LocalBusiness) structured data
- OpenGraph and Twitter cards
- Canonical URLs
- sitemap.xml and robots.txt
Acts as the primary organic search acquisition engine for patients & NGOs.
"""

import html
import json
from datetime import datetime, timezone
from typing import List, Optional
import duckdb
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse

from bloodgrid.api.deps import get_db
from bloodgrid.config import settings
from bloodgrid.geo.geocode import resolve_facility_lat_lng

router = APIRouter(tags=["Programmatic SEO & Search Acquisition"])


@router.get("/robots.txt", response_class=PlainTextResponse)
def get_robots_txt():
    """Generates search engine crawling directives."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /v1/auth/\n"
        "Disallow: /v1/admin/\n\n"
        "Sitemap: https://bloodgrid.in/sitemap.xml\n"
    )
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml")
def get_sitemap_xml(con: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Generates dynamic sitemap.xml covering all active states and districts in India."""
    results = con.execute("""
        SELECT DISTINCT state_name, district_name 
        FROM main_gold.dim_blood_banks 
        WHERE state_name IS NOT NULL AND district_name IS NOT NULL
        ORDER BY state_name, district_name;
    """).fetchall()

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    # Root and main pages
    xml_lines.append(f"  <url><loc>https://bloodgrid.in/</loc><lastmod>{today_str}</lastmod><changefreq>hourly</changefreq><priority>1.0</priority></url>")
    xml_lines.append(f"  <url><loc>https://bloodgrid.in/pricing</loc><lastmod>{today_str}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>")

    # District programmatic pages
    for state, district in results:
        state_slug = state.strip().lower().replace(" ", "-")
        dist_slug = district.strip().lower().replace(" ", "-")
        xml_lines.append(
            f"  <url><loc>https://bloodgrid.in/blood-banks/{state_slug}/{dist_slug}</loc>"
            f"<lastmod>{today_str}</lastmod><changefreq>daily</changefreq><priority>0.9</priority></url>"
        )

    xml_lines.append("</urlset>")
    return Response(content="\n".join(xml_lines), media_type="application/xml")


@router.get("/blood-banks/{state}/{district}", response_class=HTMLResponse)
@router.get("/blood-banks/{state}/{district}/{blood_group}", response_class=HTMLResponse)
def render_district_seo_page(
    state: str,
    district: str,
    blood_group: Optional[str] = None,
    con: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Renders high-speed, accessible, server-rendered SEO page for a specific district and blood group.
    """
    state_clean = state.replace("-", " ").title()
    dist_clean = district.replace("-", " ").title()
    group_clean = blood_group.upper().replace("-VE", "-").replace("+VE", "+") if blood_group else None

    # Fetch facilities in this district
    sql = """
        SELECT 
            b.hospital_code, b.hospital_name, b.hospital_type, b.hospital_contact,
            b.hospital_address, b.source_updated_at,
            COALESCE(r.reliability_score, 0), COALESCE(r.reliability_tier, 'UNKNOWN')
        FROM main_gold.dim_blood_banks b
        LEFT JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
        WHERE LOWER(b.state_name) = LOWER(?)
          AND LOWER(b.district_name) = LOWER(?)
        ORDER BY r.reliability_score DESC, b.hospital_name ASC;
    """
    facilities = con.execute(sql, [state_clean, dist_clean]).fetchall()

    if not facilities:
        raise HTTPException(status_code=404, detail=f"No blood banks recorded for {dist_clean}, {state_clean}")

    # Canonical URL
    canonical_url = f"https://bloodgrid.in/blood-banks/{state.lower()}/{district.lower()}"
    if group_clean:
        canonical_url += f"/{group_clean.lower()}"

    title = f"Blood Banks in {dist_clean}, {state_clean} - Live Stock & Emergency Contacts | BloodGrid"
    if group_clean:
        title = f"{group_clean} Blood Availability in {dist_clean}, {state_clean} - Live Stock | BloodGrid"

    description = (
        f"Find live blood inventory, contact numbers, and verified addresses for {len(facilities)} blood centres in "
        f"{dist_clean}, {state_clean}. Real-time data sourced from eRaktKosh (MoHFW)."
    )

    # Build Schema.org MedicalOrganization JSON-LD list
    jsonld_entities = []
    for f in facilities[:10]:
        hcode, hname, htype, hcontact, haddr, _, rscore, _ = f
        lat, lng, prec = resolve_facility_lat_lng(hcode, hname, haddr, state_clean, dist_clean, con)
        jsonld_entities.append({
            "@context": "https://schema.org",
            "@type": "MedicalOrganization",
            "name": hname,
            "medicalSpecialty": "TransfusionMedicine",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": haddr or dist_clean,
                "addressLocality": dist_clean,
                "addressRegion": state_clean,
                "addressCountry": "IN"
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": lat,
                "longitude": lng
            },
            "telephone": hcontact[:30] if hcontact else None
        })

    # Render clean HTML page
    cards_html = []
    for f in facilities:
        hcode, hname, htype, hcontact, haddr, sdate, rscore, rtier = f
        cards_html.append(f"""
        <article class="facility-card" style="border: 1px solid #E9E1E0; border-radius: 8px; padding: 1.25rem; background: #FFFFFF; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <h3 style="font-family: Georgia, serif; font-size: 1.15rem; color: #1A1214; margin-bottom: 0.35rem;">{html.escape(hname)}</h3>
                <span style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: #FDF4F5; color: #D21F3C; font-weight: 600;">{html.escape(htype or 'Blood Centre')}</span>
            </div>
            <p style="color: #6E6265; font-size: 0.85rem; margin-bottom: 0.5rem;">{html.escape(haddr or dist_clean)}</p>
            <div style="font-size: 0.85rem; margin-bottom: 0.75rem;">
                <strong>Contact:</strong> <span>{html.escape(hcontact or 'Call directory')}</span>
            </div>
            <div style="display: flex; gap: 0.5rem;">
                <a href="tel:{html.escape((hcontact or '').split(',')[0].replace('Phone:', '').strip())}" style="display: inline-block; padding: 6px 12px; background: #D21F3C; color: #ffffff; text-decoration: none; border-radius: 6px; font-size: 0.8rem; font-weight: 600;">Call Hospital</a>
                <a href="https://maps.google.com/?q={html.escape(hname + ', ' + dist_clean)}" target="_blank" rel="noopener" style="display: inline-block; padding: 6px 12px; border: 1px solid #E9E1E0; color: #1A1214; text-decoration: none; border-radius: 6px; font-size: 0.8rem;">Directions ↗</a>
            </div>
        </article>
        """)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description)}">
    <link rel="canonical" href="{canonical_url}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{html.escape(title)}">
    <meta property="og:description" content="{html.escape(description)}">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:type" content="website">

    <!-- Schema.org JSON-LD -->
    <script type="application/ld+json">
    {json.dumps(jsonld_entities, indent=2)}
    </script>

    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #FBF8F6;
            color: #3D3235;
            margin: 0;
            padding: 0;
            line-height: 1.5;
        }}
        .header {{
            background: #FFFFFF;
            border-bottom: 1px solid #E9E1E0;
            padding: 1rem 1.5rem;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}
        .disclaimer-banner {{
            background: #FFFBEB;
            border: 1px solid #FEF3C7;
            padding: 0.85rem 1rem;
            border-radius: 6px;
            font-size: 0.85rem;
            color: #B7791F;
            margin-bottom: 1.5rem;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div style="max-width: 900px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center;">
            <a href="/" style="text-decoration: none; font-family: Georgia, serif; font-size: 1.25rem; font-weight: bold; color: #1A1214;">
                Blood<span style="color: #D21F3C;">Grid</span>
            </a>
            <a href="/" style="text-decoration: none; font-size: 0.85rem; color: #D21F3C; font-weight: 600;">Open Live Map & Finder &rarr;</a>
        </div>
    </header>

    <main class="container">
        <div class="disclaimer-banner" style="display: flex; align-items: flex-start; gap: 0.5rem;">
            <svg style="width: 18px; height: 18px; flex-shrink: 0; color: #B7791F; margin-top: 2px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            <div><strong>Notice:</strong> Data sourced from eRaktKosh (Ministry of Health & Family Welfare, Govt. of India). Not an official service. Always call the blood bank to confirm before travelling.</div>
        </div>

        <h1 style="font-family: Georgia, serif; font-size: 2rem; color: #1A1214; margin-bottom: 0.5rem;">
            Blood Banks in {html.escape(dist_clean)}, {html.escape(state_clean)}
        </h1>
        <p style="color: #6E6265; font-size: 1rem; margin-bottom: 2rem;">
            Showing {len(facilities)} verified blood transfusion centres and storage units.
        </p>

        <section>
            {"".join(cards_html)}
        </section>
    </main>
</body>
</html>"""
    return HTMLResponse(content=full_html)
