"""
CSV Export Utility
==================
Writes plain RFC 4180 CSV that opens cleanly in Excel, Google Sheets and pandas:
- UTF-8 BOM so Excel shows non-ASCII names correctly
- header on the first row (no comment lines), CRLF line endings
- contact string split into Phone / Email columns
- cells that Excel would run as formulas are neutralised
"""

import csv
import io
import re
from typing import Any, Dict, List, Tuple

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
SOURCE = "eRaktKosh (MoHFW, Govt. of India)"


def _clean(value: Any) -> Any:
    """Collapses repeated whitespace and blocks CSV formula injection."""
    if not isinstance(value, str):
        return "" if value is None else value
    value = re.sub(r"\s+", " ", value).strip()
    # "-" alone means "not listed"; anything else starting with a formula char gets a quote prefix
    if value.startswith(_FORMULA_PREFIXES) and value != "-":
        value = "'" + value
    return value


def split_contact(contact: str) -> Tuple[str, str]:
    """Extracts (phones, email) from eRaktKosh 'Phone: a, b ,Fax: c, Email: d' strings."""
    phone_match = re.search(r"Phone:\s*([0-9\-\s,]+)", contact or "", re.I)
    phones = [p.strip() for p in phone_match.group(1).split(",")] if phone_match else []
    phones = [p for p in phones if p and p != "-"]
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", contact or "")
    return " / ".join(phones), email_match.group(0) if email_match else ""


def export_to_csv_with_bom(headers: List[str], rows: List[List[Any]]) -> str:
    output = io.StringIO()
    output.write("﻿")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_clean(v) for v in row])
    return output.getvalue()


def export_search_results_csv(items: List[Dict[str, Any]]) -> str:
    """Exports availability rows (one per bank, component and blood group)."""
    headers = [
        "Hospital Code",
        "Hospital Name",
        "State",
        "District",
        "Hospital Type",
        "Facility Type",
        "Phone",
        "Email",
        "Component",
        "Blood Group",
        "Available Units",
        "Last Updated (IST)",
        "Days Since Update",
        "Trust Score",
        "Trust Label",
        "Source",
    ]
    rows = []
    for item in items:
        phone, email = split_contact(item.get("hospital_contact", ""))
        updated = item.get("last_updated_at")
        rows.append(
            [
                item.get("hospital_code", ""),
                item.get("hospital_name", ""),
                item.get("state_name", ""),
                item.get("district_name", ""),
                item.get("hospital_type", ""),
                item.get("facility_type", ""),
                phone,
                email,
                item.get("component_name", ""),
                item.get("blood_group", ""),
                item.get("units", 0),
                str(updated)[:16] if updated else "",
                item.get("days_since_last_update", ""),
                item.get("reliability_score", ""),
                item.get("reliability_label", ""),
                SOURCE,
            ]
        )
    return export_to_csv_with_bom(headers, rows)


def export_shortages_csv(items: List[Dict[str, Any]]) -> str:
    """Exports district shortage rows."""
    headers = [
        "State",
        "District",
        "Component",
        "Blood Group",
        "Total Available Units",
        "Reporting Blood Banks",
        "Banks With Zero Stock",
        "Severity Score (0-100)",
        "Status",
        "Source",
    ]
    rows = [
        [
            item.get("state_name", ""),
            item.get("district_name", ""),
            item.get("component_name", ""),
            item.get("blood_group", ""),
            item.get("total_units", 0),
            item.get("reporting_banks", 0),
            item.get("banks_with_zero", 0),
            item.get("severity_score", ""),
            (item.get("shortage_status") or "").replace("_", " ").capitalize(),
            SOURCE,
        ]
        for item in items
    ]
    return export_to_csv_with_bom(headers, rows)
