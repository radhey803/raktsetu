"""
Generates the report's UML diagrams in black and white.

Graphviz draws the architecture, class and activity diagrams; matplotlib draws the
use case (stick-figure actors) and sequence diagrams. Fonts are large so every label
stays readable when the image is placed at full page width (about 6.2 inches).

Usage: uv run python scripts/report/generate_diagrams.py
"""

import math
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon, Rectangle

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
    # Visibility follows the code: + used by other modules, ~ helper used only inside its own
    # module (package scope), - underscore-prefixed (private). No class needs # (protected).
    classes = {
        "Settings": (
            [
                "+ warehouse_path: Path",
                "+ serving_path: Path",
                "+ scraper_concurrency: int = 10",
                "+ min_run_interval_hours: float = 6.0",
                "+ min_facility_threshold_ratio: float = 0.8",
            ],
            ["+ Settings() «reads .env»"],
        ),
        "Scraper": (
            ["~ logger: Logger"],
            [
                "+ scrape_nationwide(): list",
                "+ write_landing_parquet(): Path",
                "+ check_run_interval_guard()",
                "~ fetch_district_data(): tuple",
                "~ compute_file_sha256(): str",
            ],
        ),
        "Pipeline": (
            ["+ app: Typer", "~ console: Console"],
            [
                "+ scrape()",
                "+ load()",
                "+ transform()",
                "+ test()",
                "+ publish()",
                "+ all()",
                "+ status()",
                "~ init_metadata_tables()",
                "~ record_run_start()",
                "~ record_run_finish()",
                "~ get_last_successful_run(): dict",
                "~ ingest_landing_to_bronze(): int",
            ],
        ),
        "Database": (
            ["+ warehouse_db: Path", "+ serving_db: Path"],
            [
                "+ get_serving_connection(): Connection",
                "+ get_warehouse_connection(): Connection",
                "+ get_db_session(): Generator",
            ],
        ),
        "APIRoutes": (
            ["+ router: APIRouter"],
            [
                "+ search()",
                "+ emergency()",
                "+ history()",
                "+ shortages()",
                "+ rare()",
                "+ health_dashboard()",
                "+ export_csv()",
                "- _dbt_tests_summary(): dict",
            ],
        ),
        "MedicalRules": (
            ["~ RULES_PATH: Path", "~ PLASMA_ABO_DONORS: dict"],
            [
                "+ get_compatible_donor_groups(): tuple",
                "+ get_rules(): dict",
                "~ load_medical_rules(): dict",
                "~ is_rh_negative(): bool",
                "~ is_bombay_phenotype(): bool",
            ],
        ),
        "GeoService": (
            ["~ DISTRICT_COORDS: dict", "~ STATE_COORDS: dict", "- _LAST_NOMINATIM_CALL: float"],
            [
                "+ resolve_facility_lat_lng(): tuple",
                "+ haversine_distance_km(): float",
                "~ geocode_with_nominatim(): tuple",
                "- _load_geocoded_districts(): dict",
            ],
        ),
        "CSVExporter": (
            ["+ SOURCE: str", "- _FORMULA_PREFIXES: tuple"],
            [
                "+ export_search_results_csv(): str",
                "+ export_shortages_csv(): str",
                "~ export_to_csv_with_bom(): str",
                "~ split_contact(): tuple",
                "- _clean()",
            ],
        ),
        "CircuitBreakerError": ([""], [""]),
        "RunIntervalGuardError": ([""], [""]),
    }
    body = "  rankdir=LR; nodesep=0.3; ranksep=0.9;\n"  # left-to-right stacks classes vertically (portrait page)
    body += "\n".join(f"  {n} {_uml(n, a, o)};" for n, (a, o) in classes.items())
    body += """
  Exception [shape=box, label="«built-in»\\nException"];
  legend [shape=plain, label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
    <TR><TD ALIGN="LEFT"><B>Visibility</B></TD></TR>
    <TR><TD ALIGN="LEFT">+  public: used by other modules</TD></TR>
    <TR><TD ALIGN="LEFT">~  package: helper inside its own module</TD></TR>
    <TR><TD ALIGN="LEFT">-  private: name starts with _</TD></TR>
    <TR><TD ALIGN="LEFT">#  protected: not needed (no subclass)</TD></TR></TABLE>>];
  Pipeline -> Scraper [label=" uses"];
  Pipeline -> Database [label=" writes"];
  Scraper -> Settings [label=" reads", style=dashed];
  Database -> Settings [label=" reads", style=dashed];
  APIRoutes -> Database [label=" reads"];
  APIRoutes -> MedicalRules [label=" uses"];
  APIRoutes -> GeoService [label=" uses"];
  APIRoutes -> CSVExporter [label=" uses"];
  Scraper -> CircuitBreakerError [label=" raises", style=dashed];
  Scraper -> RunIntervalGuardError [label=" raises", style=dashed];
  CircuitBreakerError -> Exception [arrowhead=onormal];
  RunIntervalGuardError:e -> Exception:e [arrowhead=onormal];
  { rank=same; Settings; RunIntervalGuardError; CircuitBreakerError; Exception; }
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
def _actor(ax, x, y, name, label_above=False):
    ax.add_patch(plt.Circle((x, y + 0.55), 0.18, fill=False, lw=1.6))
    ax.plot([x, x], [y + 0.37, y - 0.25], "k", lw=1.6)
    ax.plot([x - 0.35, x + 0.35], [y + 0.15, y + 0.15], "k", lw=1.6)
    ax.plot([x, x - 0.28], [y - 0.25, y - 0.75], "k", lw=1.6)
    ax.plot([x, x + 0.28], [y - 0.25, y - 0.75], "k", lw=1.6)
    ty, va = (y + 0.9, "bottom") if label_above else (y - 0.95, "top")
    ax.text(x, ty, name, ha="center", va=va, fontsize=14, fontweight="bold")


# ---------------------------------------------------------------------------
# Use case diagrams (stick-figure actors, system actors, include / extend, generalization)
# Layout is fixed by hand so that no line crosses another line, ellipse or label.
# ---------------------------------------------------------------------------
EW, EH = 4.4, 0.95


def _system_actor(ax, x, y, name):
    ax.add_patch(Rectangle((x - 1.3, y - 0.65), 2.6, 1.3, fill=False, lw=1.4))
    ax.text(x, y + 0.36, "«system»", ha="center", va="center", fontsize=10.5, style="italic")
    ax.text(
        x,
        y - 0.12,
        name,
        ha="center",
        va="center",
        fontsize=11.5,
        fontweight="bold",
        linespacing=1.0,
    )


def _edge(c, toward):
    """Point on the ellipse centred at c, in the direction of `toward`."""
    dx, dy = toward[0] - c[0], toward[1] - c[1]
    t = 1 / math.hypot(dx / (EW / 2), dy / (EH / 2))
    return c[0] + dx * t, c[1] + dy * t


def draw_use_case(name, title, box, cases, actors, systems, links, rels, gens=None):
    x0, y0, x1, y1 = box
    xs = [x for _, x, _ in cases.values()] + [a[1] for a in actors] + [sy[1] for sy in systems]
    xmin, xmax = min(xs + [x0]) - 1.6, max(xs + [x1]) + 1.6
    ymin, ymax = y0 - 0.4, y1 + 0.4
    fig, ax = plt.subplots(figsize=((xmax - xmin) * 0.6, (ymax - ymin) * 0.6))
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1.3, ls="--"))
    ax.text(x0 + 0.3, y1 - 0.3, title, fontsize=14, fontweight="bold", va="top")
    pos = {}
    for cid, (label, x, y) in cases.items():
        pos[cid] = (x, y)
        ax.add_patch(Ellipse((x, y), EW, EH, fill=False, lw=1.4))
        ax.text(x, y, label, ha="center", va="center", fontsize=12)
    anchor = {}
    for aname, x, y, *opt in actors:
        _actor(ax, x, y, aname, label_above=bool(opt and opt[0]))
        anchor[aname] = (x, y + 0.15, 0.35)
    for sname, x, y in systems:
        _system_actor(ax, x, y, sname)
        anchor[sname] = (x, y, 1.3)
    for a, cid in links:
        x, y, half = anchor[a]
        c = pos[cid]
        start = (x - half if c[0] < x else x + half, y)
        end = _edge(c, start)
        ax.plot([start[0], end[0]], [start[1], end[1]], "k", lw=1.0)
    for src, dst, kind in rels:
        start, end = _edge(pos[src], pos[dst]), _edge(pos[dst], pos[src])
        ax.annotate("", end, start, arrowprops=dict(arrowstyle="->", lw=1.1, linestyle="--"))
        dx, dy = end[0] - start[0], end[1] - start[1]
        ang = math.degrees(math.atan2(dy, dx))
        if ang > 90 or ang < -90:
            ang -= 180 if ang > 0 else -180
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        if ny < 0:
            nx, ny = -nx, -ny
        mx, my = start[0] + dx * 0.5 + nx * 0.2, start[1] + dy * 0.5 + ny * 0.2
        ax.text(
            mx,
            my,
            f"«{kind}»",
            ha="center",
            va="center",
            fontsize=10.5,
            style="italic",
            rotation=ang,
            rotation_mode="anchor",
        )
    for children, parent, trunk_x in gens or []:
        px, py = next((a[1], a[2]) for a in actors if a[0] == parent)
        ys = []
        for ch in children:
            cx, cy = next((a[1], a[2]) for a in actors if a[0] == ch)
            ax.plot([cx + 0.18, trunk_x], [cy + 0.55, cy + 0.55], "k", lw=1.0)
            ys.append(cy + 0.55)
        top = py - 0.8
        ax.plot([trunk_x, trunk_x], [min(ys), top - 0.3], "k", lw=1.0)
        ax.add_patch(
            Polygon(
                [(trunk_x - 0.17, top - 0.3), (trunk_x + 0.17, top - 0.3), (trunk_x, top)],
                closed=True,
                fill=True,
                facecolor="white",
                edgecolor="black",
                lw=1.1,
            )
        )
    fig.savefig(OUT_DIR / f"{name}.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def use_case():
    c0, c1 = 4.0, 10.0
    draw_use_case(
        "use_case_diagram",
        "Raktsetu: Public Website",
        box=(1.4, -13.5, 12.6, 1.5),
        cases={
            "cmp": ("Check Blood Compatibility", c0, 0),
            "emg": ("Search Emergency Blood", c1, 0),
            "near": ("Search Near My Location", c0, -1.3),
            "map": ("View Live Map", c0, -2.6),
            "find": ("Find Blood Centres", c1, -2.6),
            "trend": ("View Trend & Trust Score", c0, -3.9),
            "net": ("View Network Statistics", c1, -3.9),
            "call": ("Call / Get Directions", c1, -5.6),
            "rare": ("Check Rare Blood", c1, -8.0),
            "csv": ("Export CSV Report", c0, -10.4),
            "short": ("View District Shortages", c1, -10.4),
            "donor": ("Check Donor Eligibility", c1, -12.9),
        },
        actors=[
            ("Public User", 16.6, -1.8, True),
            ("Patient's Family", 14.6, -5.75),
            ("Doctor / Staff", 14.6, -8.15),
            ("Health Official", 14.6, -10.55),
            ("Blood Donor", 14.6, -13.05),
        ],
        systems=[("Device GPS", -0.6, -1.3)],
        links=[
            ("Public User", "emg"),
            ("Public User", "find"),
            ("Public User", "net"),
            ("Patient's Family", "call"),
            ("Doctor / Staff", "rare"),
            ("Health Official", "short"),
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
        gens=[
            (
                ["Patient's Family", "Doctor / Staff", "Health Official", "Blood Donor"],
                "Public User",
                16.6,
            )
        ],
    )
    draw_use_case(
        "use_case_operator",
        "Raktsetu: Data Pipeline",
        box=(1.4, -9.6, 13.0, 1.5),
        cases={
            "run": ("Run Data Pipeline", c0, -2.6),
            "scrape": ("Scrape eRaktKosh Data", 10.4, 0),
            "load": ("Load Raw Data", 10.4, -1.3),
            "dbt": ("Transform with dbt", 10.4, -2.6),
            "gate": ("Run Quality Gate", 10.4, -3.9),
            "pub": ("Publish Data", 10.4, -5.2),
            "health": ("Monitor Data Health", c0, -6.0),
            "geo": ("Geocode Districts", c0, -8.6),
        },
        actors=[("Operator", -0.2, -7.45)],
        systems=[("eRaktKosh\nPortal", 14.9, 0), ("OpenStreetMap", 14.9, -8.6)],
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
