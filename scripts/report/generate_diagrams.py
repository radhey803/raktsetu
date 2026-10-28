"""
Generates the report's UML diagrams in black and white (CMPICA report style).

Graphviz draws the architecture, class and activity diagrams; matplotlib draws the
use case (stick-figure actors) and sequence diagrams. Fonts are large so every label
stays readable when the image is placed at full page width (about 6.2 inches).

Usage: uv run python scripts/report/generate_diagrams.py
"""

import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyBboxPatch, Rectangle

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "diagrams"
plt.rcParams["font.family"] = ["Liberation Serif", "DejaVu Serif"]

DOT_STYLE = """
  graph [fontname="Liberation Serif", fontsize=22, bgcolor=white, pad=0.3, nodesep=0.45, ranksep=0.45, dpi=220];
  node  [fontname="Liberation Serif", fontsize=17, color=black, fontcolor=black, penwidth=1.4, shape=box, margin="0.22,0.10"];
  edge  [fontname="Liberation Serif", fontsize=14, color=black, penwidth=1.3, arrowsize=0.9];
"""


def render_dot(name, body):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src = "digraph G {\n" + DOT_STYLE + body + "\n}\n"
    subprocess.run(
        ["dot", "-Tpng", "-o", str(OUT_DIR / f"{name}.png")], input=src.encode(), check=True
    )


# ---------------------------------------------------------------------------
# System architecture
# ---------------------------------------------------------------------------
def architecture():
    render_dot(
        "architecture_diagram",
        r"""
  rankdir=TB;
  src     [label="eRaktKosh Public Portal\n(MoHFW, Govt. of India)", shape=box3d];
  scraper [label="Async Scraper\n(aiohttp, 10 workers, retries, circuit breaker)"];
  landing [label="Landing Zone\nImmutable Parquet files + manifest", shape=folder];
  subgraph cluster_lake {
    label="DuckDB Lakehouse (built with dbt)"; style=dashed; color=black; fontsize=18;
    bronze [label="Bronze\nraw_inventory"];
    silver [label="Silver\ncleaned staging views"];
    gold   [label="Gold\nfacts, dimensions, marts"];
    bronze -> silver -> gold;
  }
  gate    [label="Quality Gate\n37 dbt tests + 80% anomaly check", shape=diamond, margin="0.05,0.05"];
  serving [label="serving.duckdb\n(read-only replica)", shape=cylinder];
  api     [label="FastAPI REST API\n/api/v1/*"];
  web     [label="Website / PWA\n(HTML, CSS, JavaScript)"];
  user    [label="Public User", shape=plaintext, fontsize=18];
  op      [label="Operator\n(make pipeline)", shape=plaintext, fontsize=18];

  src -> scraper [label=" HTTPS"];
  scraper -> landing -> bronze;
  gold -> gate;
  gate -> serving [label=" pass: atomic publish"];
  serving -> api [label=" SQL (read-only)"];
  api -> web [label=" JSON / CSV"];
  web -> user [dir=both];
  op -> scraper [style=dashed];
  {rank=same; scraper; op}
""",
    )


# ---------------------------------------------------------------------------
# Class diagram (UML boxes: name / attributes / operations)
# ---------------------------------------------------------------------------
def _uml(name, attrs, ops):
    rows = "".join(
        f'<TR><TD ALIGN="LEFT" BALIGN="LEFT">{"<BR/>".join(x)}</TD></TR>' for x in (attrs, ops)
    )
    return (
        f'[shape=plain, label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5">'
        f"<TR><TD><B>{name}</B></TD></TR>{rows}</TABLE>>]"
    )


def class_diagram():
    classes = {
        "Settings": (
            [
                "+ warehouse_path",
                "+ serving_path",
                "+ scraper_concurrency",
                "+ min_run_interval_hours",
            ],
            ["+ (pydantic settings)"],
        ),
        "Scraper": (
            ["+ concurrency: int", "+ max_retries: int"],
            [
                "+ scrape_nationwide()",
                "+ fetch_district_data()",
                "+ write_landing_parquet()",
                "+ check_run_interval_guard()",
            ],
        ),
        "Pipeline": (
            ["+ run_id: str", "+ status: str"],
            ["+ scrape()", "+ load()", "+ transform()", "+ test()", "+ publish()", "+ all()"],
        ),
        "Database": (
            ["+ warehouse.duckdb", "+ serving.duckdb"],
            ["+ get_warehouse_connection()", "+ get_serving_connection()"],
        ),
        "APIRoutes": (
            ["+ router: APIRouter"],
            [
                "+ search()",
                "+ emergency()",
                "+ history()",
                "+ shortages()",
                "+ rare()",
                "+ export_csv()",
            ],
        ),
        "MedicalRules": (
            ["+ red_cell_compatibility", "+ plasma_compatibility"],
            ["+ get_compatible_donor_groups()", "+ is_rh_negative()"],
        ),
        "GeoService": (
            ["+ district_coords"],
            ["+ resolve_facility_lat_lng()", "+ haversine_distance_km()"],
        ),
        "CSVExporter": (
            ["+ SOURCE: str"],
            ["+ export_search_results_csv()", "+ export_shortages_csv()"],
        ),
    }
    body = "  rankdir=LR; nodesep=0.3; ranksep=0.9;\n"  # left-to-right stacks classes vertically (portrait page)
    body += "\n".join(f"  {n} {_uml(n, a, o)};" for n, (a, o) in classes.items())
    body += """
  Pipeline -> Scraper [label=" uses"];
  Pipeline -> Database [label=" writes"];
  Scraper -> Settings [label=" reads", style=dashed];
  APIRoutes -> Database [label=" reads"];
  APIRoutes -> MedicalRules [label=" uses"];
  APIRoutes -> GeoService [label=" uses"];
  APIRoutes -> CSVExporter [label=" uses"];
"""
    render_dot("class_diagram", body)


# ---------------------------------------------------------------------------
# Activity diagrams
# ---------------------------------------------------------------------------
ACT = """
  rankdir=TB; nodesep=0.5; ranksep=0.35;
  node [shape=box, style=rounded];
  start [shape=circle, style=filled, fillcolor=black, label="", width=0.3];
  end   [shape=doublecircle, style=filled, fillcolor=black, label="", width=0.22];
"""


def activity_user():
    render_dot(
        "activity_diagram",
        ACT
        + """
  open    [label="Open Raktsetu website"];
  q1      [label="Emergency?", shape=diamond, style=solid];
  pick    [label="Select patient blood group\\nand component"];
  q2      [label="Use my location?", shape=diamond, style=solid];
  near    [label="Search within 50 / 150 / 400 km"];
  dist    [label="Select state and district"];
  rank    [label="View compatible groups and\\nranked blood centres"];
  filter  [label="Set filters and sort\\n(Blood Finder)"];
  cards   [label="View centre cards or map"];
  detail  [label="View 7-day trend / Trust Score"];
  act     [label="Call or get Directions"];
  start -> open -> q1;
  q1 -> pick [label=" yes"];
  q1 -> filter [label=" no"];
  pick -> q2;
  q2 -> near [label=" yes"];
  q2 -> dist [label=" no"];
  near -> rank; dist -> rank;
  filter -> cards -> detail;
  rank -> act; detail -> act;
  act -> end;
""",
    )


def activity_pipeline():
    render_dot(
        "activity_diagram_pipeline",
        ACT
        + """
  run     [label="Operator runs: make pipeline"];
  q1      [label="Last run < 6 h ago?", shape=diamond, style=solid];
  stop1   [label="Stop (interval guard)"];
  scrape  [label="Scrape all districts"];
  q2      [label="Error rate > 20%?", shape=diamond, style=solid];
  land    [label="Write immutable Parquet file"];
  load    [label="Load into Bronze"];
  dbt     [label="dbt build: Silver and Gold"];
  q3      [label="Tests pass and\\nfacilities >= 80%?", shape=diamond, style=solid];
  fail    [label="Record FAILED run\\n(old data stays online)"];
  ok      [label="Record SUCCESS run"];
  pub     [label="Publish serving.duckdb"];
  start -> run -> q1;
  q1 -> stop1 [label=" yes"];
  q1 -> scrape [label=" no"];
  scrape -> q2;
  q2 -> fail [label=" yes"];
  q2 -> land [label=" no"];
  land -> load -> dbt -> q3;
  q3 -> ok [label=" yes"];
  q3 -> fail [label=" no"];
  ok -> pub -> end;
  stop1 -> end; fail -> end;
""",
    )


# ---------------------------------------------------------------------------
# Use case diagram (stick-figure actors, ellipses, system boundary)
# ---------------------------------------------------------------------------
def _actor(ax, x, y, name):
    ax.add_patch(plt.Circle((x, y + 0.55), 0.18, fill=False, lw=1.6))
    ax.plot([x, x], [y + 0.37, y - 0.25], "k", lw=1.6)
    ax.plot([x - 0.35, x + 0.35], [y + 0.15, y + 0.15], "k", lw=1.6)
    ax.plot([x, x - 0.28], [y - 0.25, y - 0.75], "k", lw=1.6)
    ax.plot([x, x + 0.28], [y - 0.25, y - 0.75], "k", lw=1.6)
    ax.text(x, y - 1.05, name, ha="center", va="top", fontsize=15, fontweight="bold")


# ---------------------------------------------------------------------------
# Use case diagrams (stick-figure actors, system actors, include / extend)
# ---------------------------------------------------------------------------
COL_X = (4.25, 8.55)
EW, EH = 3.7, 0.8


def _system_actor(ax, x, y, name):
    ax.add_patch(Rectangle((x - 1.05, y - 0.5), 2.1, 1.0, fill=False, lw=1.4))
    ax.text(x, y + 0.18, "«system»", ha="center", va="center", fontsize=10.5, style="italic")
    ax.text(x, y - 0.16, name, ha="center", va="center", fontsize=11, fontweight="bold")


def draw_use_case(name, title, cases, actors, systems, links, rels, rows):
    fig, ax = plt.subplots(figsize=(9.5, rows * 0.92 + 1.2))
    ax.set_xlim(-0.4, 12.9)
    ax.set_ylim(-0.9, rows + 0.4)
    ax.axis("off")
    ax.add_patch(Rectangle((2.2, -0.6), 8.35, rows + 0.75, fill=False, lw=1.3, ls="--"))
    ax.text(2.6, rows + 0.05, title, fontsize=14, fontweight="bold", va="top")
    pos = {}
    for cid, (label, col, row) in cases.items():
        x, y = COL_X[col], rows - 1 - row
        pos[cid] = (x, y)
        ax.add_patch(Ellipse((x, y), EW, EH, fill=False, lw=1.4))
        ax.text(x, y, label, ha="center", va="center", fontsize=12)
    apos = {}
    for aname, row in actors:
        apos[aname] = (0.75, rows - 1 - row)
        _actor(ax, 0.75, rows - 1 - row, aname)
    for sname, row in systems:
        apos[sname] = (11.75, rows - 1 - row)
        _system_actor(ax, 11.75, rows - 1 - row, sname)
    for a, cid in links:
        ax_, ay = apos[a]
        cx, cy = pos[cid]
        if ax_ < 5:
            ax.plot([ax_ + 0.4, cx - EW / 2], [ay + 0.15, cy], "k", lw=0.9)
        else:
            ax.plot([ax_ - 1.05, cx + EW / 2], [ay, cy], "k", lw=0.9)
    for src, dst, kind in rels:
        (x1, y1), (x2, y2) = pos[src], pos[dst]
        start = (
            x1 - EW / 2 if x1 > x2 else x1 + EW / 2 if x1 < x2 else x1,
            y1 if x1 != x2 else y1 - EH / 2,
        )
        end = (
            x2 + EW / 2 if x1 > x2 else x2 - EW / 2 if x1 < x2 else x2,
            y2 if x1 != x2 else y2 + EH / 2,
        )
        ax.annotate("", end, start, arrowprops=dict(arrowstyle="->", lw=1.1, linestyle="--"))
        mx, my = start[0] + (end[0] - start[0]) * 0.6, start[1] + (end[1] - start[1]) * 0.6
        ax.text(mx, my + 0.1, f"«{kind}»", ha="center", va="bottom", fontsize=10, style="italic")
    fig.savefig(OUT_DIR / f"{name}.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def use_case():
    draw_use_case(
        "use_case_diagram",
        "Raktsetu: Public Website",
        cases={
            "emg": ("Search Emergency Blood", 0, 0),
            "cmp": ("Check Blood Compatibility", 1, 0),
            "near": ("Search Near My Location", 1, 1),
            "find": ("Find Blood Centres", 0, 2),
            "map": ("View Live Map", 1, 2),
            "trend": ("View Trend & Trust Score", 1, 3),
            "call": ("Call / Get Directions", 0, 4),
            "rare": ("Check Rare Blood", 0, 5),
            "short": ("View District Shortages", 0, 6),
            "csv": ("Export CSV Report", 1, 6),
            "net": ("View Network Statistics", 0, 7),
            "donor": ("Check Donor Eligibility", 0, 8),
        },
        actors=[
            ("Patient's Family", 0.2),
            ("Doctor / Staff", 2.6),
            ("Health Official", 5.0),
            ("Blood Donor", 7.4),
        ],
        systems=[("Device GPS", 1.1)],
        links=[
            ("Patient's Family", "emg"),
            ("Patient's Family", "find"),
            ("Patient's Family", "call"),
            ("Doctor / Staff", "emg"),
            ("Doctor / Staff", "find"),
            ("Doctor / Staff", "rare"),
            ("Health Official", "find"),
            ("Health Official", "short"),
            ("Health Official", "net"),
            ("Blood Donor", "net"),
            ("Blood Donor", "donor"),
            ("Device GPS", "near"),
        ],
        rels=[
            ("emg", "cmp", "include"),
            ("near", "emg", "extend"),
            ("map", "find", "extend"),
            ("trend", "find", "extend"),
            ("csv", "short", "extend"),
        ],
        rows=9,
    )
    draw_use_case(
        "use_case_operator",
        "Raktsetu: Data Pipeline",
        cases={
            "run": ("Run Data Pipeline", 0, 2),
            "scrape": ("Scrape eRaktKosh Data", 1, 0),
            "load": ("Load Raw Data", 1, 1),
            "dbt": ("Transform with dbt", 1, 2),
            "gate": ("Run Quality Gate", 1, 3),
            "pub": ("Publish Data", 1, 4),
            "health": ("Monitor Data Health", 0, 5),
            "geo": ("Geocode Districts", 1, 6),
        },
        actors=[("Operator", 3.0)],
        systems=[("eRaktKosh\nPortal", 0), ("OpenStreetMap", 6)],
        links=[
            ("Operator", "run"),
            ("Operator", "health"),
            ("Operator", "geo"),
            ("eRaktKosh\nPortal", "scrape"),
            ("OpenStreetMap", "geo"),
        ],
        rels=[
            ("run", "scrape", "include"),
            ("run", "load", "include"),
            ("run", "dbt", "include"),
            ("run", "gate", "include"),
            ("run", "pub", "include"),
        ],
        rows=7,
    )


# ---------------------------------------------------------------------------
# Sequence diagram: emergency search
# ---------------------------------------------------------------------------
def sequence():
    parts = ["User", "Website\n(Browser)", "FastAPI", "Medical\nRules", "DuckDB\n(serving)"]
    msgs = [
        (0, 1, "Select group, component,\nlocation", False),
        (1, 2, "GET /api/v1/emergency", False),
        (2, 3, "get_compatible_donor_groups()", False),
        (3, 2, "compatible groups", True),
        (2, 4, "SQL: stock + trust scores", False),
        (4, 2, "matching facilities", True),
        (2, 2, "distance & rank score", False),
        (2, 1, "JSON: top facilities", True),
        (1, 0, "Ranked cards with\nCall / Directions", True),
    ]
    fig, ax = plt.subplots(figsize=(8.5, 9.5))
    xs = [0.9 + i * 2.05 for i in range(len(parts))]
    top, bottom = 10.0, 0.4
    ax.set_xlim(0, 10.2)
    ax.set_ylim(0, 11)
    ax.axis("off")
    for x, name in zip(xs, parts, strict=True):
        ax.add_patch(
            FancyBboxPatch((x - 0.8, top), 1.6, 0.75, boxstyle="square,pad=0", fill=False, lw=1.4)
        )
        ax.text(x, top + 0.375, name, ha="center", va="center", fontsize=13, fontweight="bold")
        ax.plot([x, x], [top, bottom], "k--", lw=0.9)
    y = top - 1.1
    for a, b, text, reply in msgs:
        if a == b:
            x = xs[a]
            ax.plot([x, x + 0.6, x + 0.6, x + 0.05], [y, y, y - 0.45, y - 0.45], "k", lw=1.2)
            ax.annotate(
                "",
                (x + 0.05, y - 0.45),
                (x + 0.3, y - 0.45),
                arrowprops=dict(arrowstyle="->", lw=1.2),
            )
            ax.text(x + 0.7, y - 0.22, text, fontsize=12, va="center")
            y -= 1.0
            continue
        ax.annotate(
            "",
            (xs[b], y),
            (xs[a], y),
            arrowprops=dict(arrowstyle="->", lw=1.2, linestyle="--" if reply else "-"),
        )
        ax.text((xs[a] + xs[b]) / 2, y + 0.1, text, ha="center", va="bottom", fontsize=12)
        y -= 1.0
    fig.savefig(OUT_DIR / "sequence_diagram.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Data flow diagrams, ER diagram and Gantt chart
# ---------------------------------------------------------------------------
def dfd_level0():
    render_dot(
        "dfd_level0",
        r"""
  rankdir=LR; nodesep=0.7; ranksep=1.1;
  src  [label="eRaktKosh\nPortal"];  osm [label="OpenStreetMap"];
  user [label="Public User"];        op  [label="Operator"];
  sys  [label="0\nRaktsetu\nSystem", shape=circle, width=2.0, fixedsize=true, fontsize=19];
  src -> sys  [label="blood stock data"];
  osm -> sys  [label="district coordinates"];
  user -> sys [label="search filters,\nblood group, location"];
  sys -> user [label="ranked blood centres,\nmaps, trends, reports"];
  op -> sys   [label="run pipeline"];
  sys -> op   [label="run status,\ndata health"];
  {rank=same; src; osm}  {rank=same; user; op}
""",
    )


def dfd_level1():
    render_dot(
        "dfd_level1",
        r"""
  rankdir=TB; nodesep=0.55; ranksep=0.55;
  node [shape=ellipse];
  src [label="eRaktKosh Portal", shape=box]; osm [label="OpenStreetMap", shape=box];
  op  [label="Operator", shape=box];         user [label="Public User", shape=box];
  p1 [label="1.0\nCollect Stock Data"]; p2 [label="2.0\nLoad Raw Data"];
  p3 [label="3.0\nTransform & Validate"]; p4 [label="4.0\nPublish Data"];
  p5 [label="5.0\nSearch & Rank"]; p6 [label="6.0\nAnalytics & Export"];
  node [shape=record];
  d1 [label="D1 | Landing Parquet Files"]; d2 [label="D2 | Warehouse (Bronze, Silver, Gold)"];
  d3 [label="D3 | Serving Database"]; d4 [label="D4 | District Coordinates"];
  op -> p1 [label="start run"]; src -> p1 [label="stock data"]; p1 -> d1 [label="raw records"];
  d1 -> p2; p2 -> d2 [label="bronze rows"]; d2 -> p3 [label="raw rows"];
  p3 -> d2 [label="clean tables"]; p3 -> p4 [label="test results"]; d2 -> p4;
  p4 -> d3 [label="published copy"]; p4 -> op [label="run status"];
  osm -> d4 [label="coordinates"];
  d3 -> p5; d4 -> p5; user -> p5 [label="search request"]; p5 -> user [label="ranked results"];
  d3 -> p6; p6 -> user [label="shortages, trends, CSV"];
""",
    )


def _entity(name, fields):
    rows = "".join(f'<TR><TD ALIGN="LEFT">{f}</TD></TR>' for f in fields)
    return (
        f'[shape=plain, label=<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
        f"<TR><TD><B>{name}</B></TD></TR>{rows}</TABLE>>]"
    )


def er_diagram():
    ents = {
        "BLOOD_CENTRE": [
            "<U>hospital_code</U> (PK)",
            "hospital_name",
            "hospital_type",
            "state_name",
            "district_name",
            "hospital_contact",
            "source_updated_at",
        ],
        "STOCK_SNAPSHOT": [
            "<U>hospital_code</U> (FK)",
            "<U>component_name</U>",
            "<U>blood_group</U>",
            "<U>snapshot_date</U>",
            "units",
        ],
        "CURRENT_STOCK": [
            "<U>hospital_code</U> (FK)",
            "<U>component_name</U>",
            "<U>blood_group</U>",
            "units",
            "last_synced_at",
        ],
        "RELIABILITY_SCORE": [
            "<U>hospital_code</U> (PK, FK)",
            "freshness_points",
            "contact_points",
            "completeness_points",
            "reliability_score",
        ],
        "RARE_BLOOD": [
            "hospital_code (FK)",
            "blood_group",
            "component_name",
            "units",
            "rarity_tier",
        ],
        "DISTRICT_STATUS": [
            "<U>state_name</U>",
            "<U>district_name</U>",
            "<U>component_name</U>",
            "<U>blood_group</U>",
            "total_units",
            "severity_score",
            "shortage_status",
        ],
        "PIPELINE_RUN": [
            "<U>run_id</U> (PK)",
            "started_at",
            "finished_at",
            "status",
            "facilities_count",
        ],
        "RAW_INVENTORY": ["run_id (FK)", "hospital_code", "scraped_at", "components_raw"],
    }
    body = "  rankdir=TB; nodesep=0.4; ranksep=0.7;\n"
    body += "\n".join(f"  {n} {_entity(n, f)};" for n, f in ents.items())
    body += """
  BLOOD_CENTRE -> STOCK_SNAPSHOT [label=" 1 : N", arrowhead=crow];
  BLOOD_CENTRE -> CURRENT_STOCK [label=" 1 : N", arrowhead=crow];
  BLOOD_CENTRE -> RELIABILITY_SCORE [label=" 1 : 1", arrowhead=tee];
  BLOOD_CENTRE -> RARE_BLOOD [label=" 1 : N", arrowhead=crow];
  CURRENT_STOCK -> DISTRICT_STATUS [label=" aggregated into", style=dashed];
  PIPELINE_RUN -> RAW_INVENTORY [label=" 1 : N", arrowhead=crow];
  RAW_INVENTORY -> BLOOD_CENTRE [label=" builds", style=dashed];
  {rank=same; PIPELINE_RUN; RAW_INVENTORY}
"""
    render_dot("er_diagram", body)


def gantt():
    tasks = [
        ("Requirement study & eRaktKosh analysis", 1, 2),
        ("System design & diagrams", 2, 3),
        ("Async scraper & landing zone", 3, 3),
        ("Lakehouse & dbt models", 5, 4),
        ("REST API development", 7, 3),
        ("Website, map & PWA", 8, 5),
        ("Testing & bug fixing", 11, 4),
        ("Documentation & report", 13, 4),
    ]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for i, (_name, start, length) in enumerate(tasks):
        ax.barh(
            i,
            length,
            left=start - 0.5,
            height=0.55,
            color="white",
            edgecolor="black",
            hatch="///",
            lw=1.2,
        )
    ax.set_yticks(range(len(tasks)), [t[0] for t in tasks], fontsize=12)
    ax.invert_yaxis()
    ax.set_xticks(range(1, 17), [str(w) for w in range(1, 17)], fontsize=11)
    ax.set_xlim(0.5, 16.5)
    ax.set_xlabel("Week", fontsize=13)
    ax.grid(axis="x", ls=":", color="black", lw=0.5)
    fig.savefig(OUT_DIR / "gantt_chart.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    for fn in (
        architecture,
        class_diagram,
        activity_user,
        activity_pipeline,
        use_case,
        sequence,
        dfd_level0,
        dfd_level1,
        er_diagram,
        gantt,
    ):
        fn()
    print(f"11 black-and-white diagrams written to {OUT_DIR}")
