"""
Generates the report's UML diagrams in black and white.

Graphviz draws the architecture, class and activity diagrams; matplotlib draws the
use case (stick-figure actors) and sequence diagrams. Fonts are large so every label
stays readable when the image is placed at full page width (about 6.2 inches).

Usage: uv run python scripts/report/generate_diagrams.py
"""

import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle

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


if __name__ == "__main__":
    for fn in (
        class_diagram,
        activity_user,
        activity_pipeline,
        use_case,
    ):
        fn()
    print(f"5 black-and-white diagrams written to {OUT_DIR}")
