"""
CSV Export Utility with UTF-8 BOM for Excel
===========================================
Formats tabular search results and shortage reports into valid CSV with:
- UTF-8 BOM (\\ufeff) for flawless Excel display without character corruption
- Metadata header rows with generation timestamp and MoHFW attribution
- Quoted fields to prevent delimiter collisions
"""

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List


def export_to_csv_with_bom(
    headers: List[str],
    rows: List[List[Any]],
    title: str = "Blood Inventory Export",
) -> str:
    """
    Exports rows to a CSV string prefixed with UTF-8 BOM and metadata header comments.
    """
    output = io.StringIO()
    # Write UTF-8 BOM
    output.write("\ufeff")

    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    output.write(f"# {title} - Generated at: {timestamp_str}\n")
    output.write(
        "# Data sourced from eRaktKosh (MoHFW, Govt. of India). Academic research project, not an official service.\n"
    )
    output.write("# Call the blood bank directly to confirm live unit availability before travelling.\n")

    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    return output.getvalue()


def export_search_results_csv(items: List[Dict[str, Any]]) -> str:
    """Exports availability search items to formatted CSV."""
    headers = [
        "Hospital Code",
        "Hospital Name",
        "State",
        "District",
        "Hospital Type",
        "Facility Type",
        "Contact",
        "Component",
        "Blood Group",
        "Available Units",
        "Reliability Score",
        "Reliability Label",
        "Days Since Update",
        "Location Precision",
    ]
    rows = []
    for item in items:
        rows.append(
            [
                item.get("hospital_code", ""),
                item.get("hospital_name", ""),
                item.get("state_name", ""),
                item.get("district_name", ""),
                item.get("hospital_type", ""),
                item.get("facility_type", ""),
                item.get("hospital_contact", ""),
                item.get("component_name", ""),
                item.get("blood_group", ""),
                item.get("units", 0),
                item.get("reliability_score", 50),
                item.get("reliability_label", "Medium"),
                item.get("days_since_last_update", ""),
                item.get("location_precision", "district_centroid"),
            ]
        )
    return export_to_csv_with_bom(headers, rows, title="eRaktKosh Availability Search Export")


def export_shortages_csv(items: List[Dict[str, Any]]) -> str:
    """Exports district shortage items to formatted CSV."""
    headers = [
        "State",
        "District",
        "Component",
        "Blood Group",
        "Total Available Units",
        "Reporting Blood Banks",
        "Banks With Zero Stock",
        "Shortage Severity Status",
    ]
    rows = []
    for item in items:
        rows.append(
            [
                item.get("state_name", ""),
                item.get("district_name", ""),
                item.get("component_name", ""),
                item.get("blood_group", ""),
                item.get("total_units", 0),
                item.get("reporting_banks", 0),
                item.get("banks_with_zero", 0),
                item.get("shortage_status", "UNKNOWN"),
            ]
        )
    return export_to_csv_with_bom(headers, rows, title="eRaktKosh District Shortage Radar Export")
