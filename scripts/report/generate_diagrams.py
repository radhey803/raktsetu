from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Set standard aesthetic style
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9


def create_system_architecture():
    fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    ax.text(
        7,
        9.6,
        "Raktsetu: Modern Medallion Lakehouse Architecture",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="#1A1214",
    )
    ax.text(
        7,
        9.25,
        "National Blood Inventory Intelligence & Emergency Triage Engine",
        ha="center",
        va="center",
        fontsize=10,
        fontstyle="italic",
        color="#555555",
    )

    # Color palette
    c_ingest = "#E0F2FE"  # Sky Blue
    c_bronze = "#FED7AA"  # Warm Amber/Bronze
    c_silver = "#E2E8F0"  # Slate/Silver
    c_gold = "#FEF08A"  # Goldenrod
    c_gate = "#DCFCE7"  # Emerald Green

    # Box 1: Ingestion Layer
    rect1 = patches.FancyBboxPatch(
        (0.5, 6.2), 3.6, 2.7, boxstyle="round,pad=0.2", ec="#0284C7", fc=c_ingest, lw=1.5
    )
    ax.add_patch(rect1)
    ax.text(
        2.3,
        8.6,
        "1. Asynchronous Ingestion Layer",
        ha="center",
        fontweight="bold",
        color="#0369A1",
        fontsize=11,
    )
    ax.text(
        2.3,
        7.8,
        "• eRaktKosh Public Portal\n  (781 Administrative Districts)\n• Async Scraper (Semaphore: 10)\n• Exponential Backoff & Jitter\n• Immutable Parquet Landing\n• SHA-256 Checksum Validation",
        ha="center",
        va="center",
        color="#0F172A",
        fontsize=8.5,
        linespacing=1.3,
    )

    # Box 2: Medallion Lakehouse (DuckDB + dbt)
    rect2 = patches.FancyBboxPatch(
        (4.7, 4.8), 4.6, 4.1, boxstyle="round,pad=0.2", ec="#EA580C", fc="#FFFBEB", lw=1.5
    )
    ax.add_patch(rect2)
    ax.text(
        7.0,
        8.6,
        "2. Medallion Lakehouse (DuckDB + dbt)",
        ha="center",
        fontweight="bold",
        color="#C2410C",
        fontsize=11,
    )

    # Bronze sub-box
    ax.add_patch(
        patches.FancyBboxPatch(
            (4.9, 7.3), 4.2, 0.9, boxstyle="round,pad=0.1", ec="#D97706", fc=c_bronze, lw=1
        )
    )
    ax.text(
        7.0,
        7.75,
        "BRONZE LAYER (Append-Only Raw)",
        ha="center",
        fontweight="bold",
        fontsize=8.5,
        color="#92400E",
    )
    ax.text(
        7.0,
        7.45,
        "raw_blood_inventory (Raw schema, batch timestamp)",
        ha="center",
        fontsize=7.5,
        color="#78350F",
    )

    # Silver sub-box
    ax.add_patch(
        patches.FancyBboxPatch(
            (4.9, 6.1), 4.2, 0.9, boxstyle="round,pad=0.1", ec="#64748B", fc=c_silver, lw=1
        )
    )
    ax.text(
        7.0,
        6.55,
        "SILVER LAYER (Cleansed & Conformed)",
        ha="center",
        fontweight="bold",
        fontsize=8.5,
        color="#334155",
    )
    ax.text(
        7.0,
        6.25,
        "stg_blood_banks | stg_inventory_components (Regex Isolated)",
        ha="center",
        fontsize=7.5,
        color="#1E293B",
    )

    # Gold sub-box
    ax.add_patch(
        patches.FancyBboxPatch(
            (4.9, 4.9), 4.2, 0.9, boxstyle="round,pad=0.1", ec="#CA8A04", fc=c_gold, lw=1
        )
    )
    ax.text(
        7.0,
        5.35,
        "GOLD LAYER (Dimensional Marts)",
        ha="center",
        fontweight="bold",
        fontsize=8.5,
        color="#854D0E",
    )
    ax.text(
        7.0,
        5.05,
        "dim_blood_banks | fct_stock_current | mart_reliability_score\nmart_district_status | mart_rare_blood | mart_stock_change",
        ha="center",
        fontsize=7,
        color="#713F12",
    )

    # Box 3: Dual-Database Quality Gate
    rect3 = patches.FancyBboxPatch(
        (10.0, 5.2), 3.5, 3.7, boxstyle="round,pad=0.2", ec="#16A34A", fc=c_gate, lw=1.5
    )
    ax.add_patch(rect3)
    ax.text(
        11.75,
        8.6,
        "3. Quality Gate & Atomic Swap",
        ha="center",
        fontweight="bold",
        color="#15803D",
        fontsize=11,
    )
    ax.text(
        11.75,
        7.0,
        "• 37 dbt Integrity Tests\n  (Unique, Non-null, Accepted Vals)\n• Anomaly & Threshold Gate\n  (Active count >= 80% baseline)\n• Atomic Copy & Swap:\n  blood_warehouse -> serving.duckdb\n• Read-Only Production Isolation\n• Zero-Downtime Hot Reload",
        ha="center",
        va="center",
        color="#064E3B",
        fontsize=8.5,
        linespacing=1.3,
    )

    # Box 4: Serving & Clinical Interface
    rect4 = patches.FancyBboxPatch(
        (1.5, 0.8), 11.0, 3.2, boxstyle="round,pad=0.2", ec="#BE185D", fc="#FDF2F8", lw=1.5
    )
    ax.add_patch(rect4)
    ax.text(
        7.0,
        3.6,
        "4. Analytical Serving & Clinical Web Interface",
        ha="center",
        fontweight="bold",
        color="#9D174D",
        fontsize=12,
    )

    # Fast API sub-box
    ax.add_patch(
        patches.FancyBboxPatch(
            (1.8, 1.2), 4.8, 2.0, boxstyle="round,pad=0.1", ec="#0284C7", fc="#F0F9FF", lw=1
        )
    )
    ax.text(
        4.2,
        2.9,
        "FastAPI High-Concurrency Backend",
        ha="center",
        fontweight="bold",
        fontsize=9.5,
        color="#0369A1",
    )
    ax.text(
        4.2,
        2.0,
        "• /api/v1/availability (District & State query)\n• /api/v1/emergency (Multi-criteria triage)\n• /api/v1/shortages (District deficit rankings)\n• /api/v1/rare (Rare blood & Bombay radar)\n• /api/v1/health/dashboard (Freshness audit)",
        ha="center",
        va="center",
        fontsize=7.8,
        color="#0C4A6E",
    )

    # Frontend sub-box
    ax.add_patch(
        patches.FancyBboxPatch(
            (7.4, 1.2), 4.8, 2.0, boxstyle="round,pad=0.1", ec="#BE123C", fc="#FFF1F2", lw=1
        )
    )
    ax.text(
        9.8,
        2.9,
        "Clinical Vanilla Web Application",
        ha="center",
        fontweight="bold",
        fontsize=9.5,
        color="#9F1239",
    )
    ax.text(
        9.8,
        2.0,
        "• Carto Positron Vector Basemaps & Leaflet.js\n• Chart.js Historical Stock Snapshots\n• Trilingual Interface (English, Hindi, Gujarati)\n• 100% Private Client-Side Donor Calculator\n• Zero-Emoji Design System & Inline SVG\n• Progressive Web App (PWA) Offline Replay",
        ha="center",
        va="center",
        fontsize=7.8,
        color="#881337",
    )

    # Connective Arrows
    # Ingestion -> Lakehouse
    ax.annotate(
        "",
        xy=(4.7, 7.5),
        xytext=(4.1, 7.5),
        arrowprops=dict(arrowstyle="-|>", lw=2, color="#0284C7"),
    )
    # Lakehouse -> Quality Gate
    ax.annotate(
        "",
        xy=(10.0, 7.0),
        xytext=(9.3, 7.0),
        arrowprops=dict(arrowstyle="-|>", lw=2, color="#EA580C"),
    )
    # Quality Gate -> Serving (Downwards)
    ax.annotate(
        "",
        xy=(9.0, 4.0),
        xytext=(11.5, 5.2),
        arrowprops=dict(arrowstyle="-|>", lw=2, color="#16A34A", connectionstyle="arc3,rad=-0.2"),
    )
    # Ingestion/Lakehouse to API
    ax.annotate(
        "",
        xy=(5.0, 4.0),
        xytext=(7.0, 4.8),
        arrowprops=dict(arrowstyle="-|>", lw=2, color="#64748B"),
    )

    plt.tight_layout()
    plt.savefig(OUT_DIR / "architecture_diagram.png", bbox_inches="tight", dpi=300)
    plt.close()
    print("Architecture diagram generated.")


def create_use_case_diagram():
    fig, ax = plt.subplots(figsize=(15, 12), dpi=300)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 12)
    ax.axis("off")

    # Title
    ax.text(
        7.5,
        11.6,
        "Raktsetu: UML Use Case Diagram",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="#1A1214",
    )
    ax.text(
        7.5,
        11.25,
        "Standard UML Model with Direct Associations, <<include>>, and <<extend>> Relationships",
        ha="center",
        va="center",
        fontsize=10,
        fontstyle="italic",
        color="#555555",
    )

    # System boundary
    rect = patches.FancyBboxPatch(
        (3.8, 0.5), 7.4, 10.3, boxstyle="round,pad=0.2", ec="#0F172A", fc="#F8FAFC", lw=2, ls="--"
    )
    ax.add_patch(rect)
    ax.text(
        7.5,
        10.5,
        "System Boundary: Raktsetu National Blood Lakehouse",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#0F172A",
    )

    # Clean non-overlapping Use Cases
    # (x, y, w, h, text, bg, border)
    ucs = [
        (
            6.0,
            9.7,
            3.4,
            0.75,
            "UC1: Search Inventory\n(District & Blood Group)",
            "#E0F2FE",
            "#0284C7",
        ),
        (5.8, 8.6, 3.2, 0.75, "UC2: Initiate Emergency\nTriage Mode", "#FEE2E2", "#DC2626"),
        (
            9.4,
            8.6,
            3.1,
            0.75,
            "UC3: Resolve Compatibility\n(WHO/NBTC Matrix)",
            "#FEF3C7",
            "#D97706",
        ),
        (
            9.4,
            7.5,
            3.1,
            0.75,
            "UC4: Geolocation Proximity\n& Distance Filter",
            "#F1F5F9",
            "#475569",
        ),
        (5.8, 7.5, 3.2, 0.75, "UC5: Inspect 3-Pillar\nTrust Score Modal", "#DCFCE7", "#16A34A"),
        (
            6.0,
            6.4,
            3.4,
            0.75,
            "UC6: View Historical Trend\n& Depletion Flags",
            "#E0E7FF",
            "#4F46E5",
        ),
        (6.0, 5.3, 3.4, 0.75, "UC7: Calculate Donor\nEligibility (Private)", "#FCE7F3", "#DB2777"),
        (
            6.0,
            4.2,
            3.4,
            0.75,
            "UC8: Export Emergency Roster\n(Excel CSV / WhatsApp)",
            "#CFFAFE",
            "#0891B2",
        ),
        (
            6.0,
            3.1,
            3.4,
            0.75,
            "UC9: Audit District Deficits\n& Shortage Radar",
            "#FFEDD5",
            "#EA580C",
        ),
        (
            6.0,
            2.0,
            3.4,
            0.75,
            "UC10: Monitor Lakehouse Health\n& Freshness Metrics",
            "#CCFBF1",
            "#0D9488",
        ),
        (6.0, 0.9, 3.4, 0.75, "UC11: Update & Synchronize\nBed-Side Stock", "#EDE9FE", "#7C3AED"),
    ]

    for x, y, w, h, label, bg, border in ucs:
        ellipse = patches.Ellipse((x, y), w, h, ec=border, fc=bg, lw=1.5)
        ax.add_patch(ellipse)
        ax.text(
            x, y, label, ha="center", va="center", fontsize=7.5, fontweight="bold", color="#1E293B"
        )

    # Relationships between use cases
    # UC2 <<include>> UC3
    ax.annotate(
        "",
        xy=(7.85, 8.6),
        xytext=(7.4, 8.6),
        arrowprops=dict(arrowstyle="->", ls="--", lw=1.3, color="#D97706"),
    )
    ax.text(7.6, 8.85, "<<include>>", fontsize=7, color="#B45309", ha="center", fontweight="bold")

    # UC2 <<extend>> UC4
    ax.annotate(
        "",
        xy=(7.4, 8.4),
        xytext=(8.0, 7.7),
        arrowprops=dict(arrowstyle="<-", ls="--", lw=1.3, color="#475569"),
    )
    ax.text(7.9, 8.1, "<<extend>>", fontsize=7, color="#334155", ha="center", fontweight="bold")

    # Actor 1: Emergency Requester / Caregiver (Left)
    ax.plot(1.8, 6.8, "o", ms=20, mfc="#E2E8F0", mec="#0F172A", mew=2)
    ax.plot([1.8, 1.8], [6.5, 5.2], color="#0F172A", lw=2.5)
    ax.plot([1.1, 2.5], [5.9, 5.9], color="#0F172A", lw=2.5)
    ax.plot([1.8, 1.2], [5.2, 4.0], color="#0F172A", lw=2.5)
    ax.plot([1.8, 2.4], [5.2, 4.0], color="#0F172A", lw=2.5)
    ax.text(
        1.8,
        3.5,
        "Emergency Requester\n/ General Citizen",
        ha="center",
        fontweight="bold",
        fontsize=9.5,
        color="#0F172A",
    )

    # Lines from Requester to UCs
    for target_x, target_y in [
        (4.3, 9.7),
        (4.2, 8.6),
        (4.2, 7.5),
        (4.3, 6.4),
        (4.3, 5.3),
        (4.3, 4.2),
    ]:
        ax.annotate(
            "",
            xy=(target_x, target_y),
            xytext=(2.2, 5.9),
            arrowprops=dict(arrowstyle="-", lw=1.2, color="#334155"),
        )

    # Actor 2: Regional Health Officer (Right Top)
    ax.plot(13.2, 8.2, "o", ms=18, mfc="#E2E8F0", mec="#0F172A", mew=2)
    ax.plot([13.2, 13.2], [7.9, 6.8], color="#0F172A", lw=2.5)
    ax.plot([12.6, 13.8], [7.4, 7.4], color="#0F172A", lw=2.5)
    ax.plot([13.2, 12.7], [6.8, 5.8], color="#0F172A", lw=2.5)
    ax.plot([13.2, 13.7], [6.8, 5.8], color="#0F172A", lw=2.5)
    ax.text(
        13.2,
        5.3,
        "Regional Health Officer\n/ Decision Maker",
        ha="center",
        fontweight="bold",
        fontsize=9,
        color="#0F172A",
    )

    # Lines from Health Officer to UCs
    for target_x, target_y in [(7.7, 4.2), (7.7, 3.1), (7.7, 2.0)]:
        ax.annotate(
            "",
            xy=(target_x, target_y),
            xytext=(12.5, 7.4),
            arrowprops=dict(arrowstyle="-", lw=1.2, color="#0F172A"),
        )

    # Actor 3: Blood Bank Officer (Right Bottom)
    ax.plot(13.2, 3.2, "o", ms=18, mfc="#E2E8F0", mec="#0F172A", mew=2)
    ax.plot([13.2, 13.2], [2.9, 1.8], color="#0F172A", lw=2.5)
    ax.plot([12.6, 13.8], [2.4, 2.4], color="#0F172A", lw=2.5)
    ax.plot([13.2, 12.7], [1.8, 0.8], color="#0F172A", lw=2.5)
    ax.plot([13.2, 13.7], [1.8, 0.8], color="#0F172A", lw=2.5)
    ax.text(
        13.2,
        0.4,
        "Blood Bank Staff\n/ System Operator",
        ha="center",
        fontweight="bold",
        fontsize=9,
        color="#0F172A",
    )

    # Lines from Operator to UCs
    for target_x, target_y in [(7.7, 2.0), (7.7, 0.9), (7.4, 7.5)]:
        ax.annotate(
            "",
            xy=(target_x, target_y),
            xytext=(12.5, 2.4),
            arrowprops=dict(arrowstyle="-", lw=1.2, color="#0F172A"),
        )

    plt.tight_layout()
    plt.savefig(OUT_DIR / "use_case_diagram.png", bbox_inches="tight", dpi=300)
    plt.close()
    print("Use case diagram generated.")


def create_class_diagram():
    fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    ax.text(
        7,
        9.6,
        "Raktsetu: UML Domain Model & Class Diagram",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="#1A1214",
    )
    ax.text(
        7,
        9.25,
        "Clean Data Modeling: Entities, Value Objects, and Mart Aggregates",
        ha="center",
        va="center",
        fontsize=10,
        fontstyle="italic",
        color="#555555",
    )

    def draw_class(x, y, w, h, name, attrs, methods, header_col="#0284C7"):
        # Header box
        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y + h - 0.7),
                w,
                0.7,
                boxstyle="round,pad=0.0",
                ec="#334155",
                fc=header_col,
                lw=1.2,
            )
        )
        ax.text(
            x + w / 2,
            y + h - 0.35,
            name,
            ha="center",
            va="center",
            fontweight="bold",
            color="white",
            fontsize=9,
        )
        # Body box
        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y), w, h - 0.7, boxstyle="round,pad=0.0", ec="#334155", fc="#FFFFFF", lw=1.2
            )
        )
        # Attributes
        attr_text = "\n".join(attrs)
        ax.text(
            x + 0.15,
            y + h - 0.9,
            attr_text,
            va="top",
            fontsize=7.2,
            color="#0F172A",
            linespacing=1.2,
        )
        # Divider line
        div_y = y + len(methods) * 0.35 + 0.15
        ax.plot([x, x + w], [div_y, div_y], color="#CBD5E1", lw=1)
        # Methods
        method_text = "\n".join(methods)
        ax.text(
            x + 0.15,
            div_y - 0.1,
            method_text,
            va="top",
            fontsize=7.2,
            color="#1E3A8A",
            fontstyle="italic",
            linespacing=1.2,
        )

    # Class 1: BloodBank (Center)
    draw_class(
        0.8,
        4.8,
        3.8,
        3.8,
        "BloodBank (Entity)",
        [
            "- facility_id: String [PK]",
            "- facility_name: String",
            "- state: String",
            "- district: String",
            "- contact_phone: String",
            "- address: String",
            "- latitude: Double",
            "- longitude: Double",
            "- last_updated: Timestamp",
            "- category: String (Govt/RedCross/Pvt)",
        ],
        [
            "+ compute_distance(lat, lon): Double",
            "+ get_formatted_phone(): String",
            "+ is_stale(max_hours): Boolean",
        ],
        "#0369A1",
    )

    # Class 2: BloodComponent (Right of BloodBank)
    draw_class(
        5.5,
        5.2,
        3.6,
        3.4,
        "BloodComponent (Entity)",
        [
            "- component_id: String [PK]",
            "- facility_id: String [FK]",
            "- blood_group: BloodGroupEnum",
            "- component_type: ComponentEnum",
            "- quantity_units: Integer",
            "- snapshot_time: Timestamp",
            "- availability_flag: Boolean",
        ],
        ["+ is_rare_phenotype(): Boolean", "+ format_stock_label(): String"],
        "#0D9488",
    )

    # Class 3: ReliabilityScore (Below BloodBank)
    draw_class(
        0.8,
        0.8,
        3.8,
        3.2,
        "ReliabilityScore (Value Object)",
        [
            "- facility_id: String [FK]",
            "- freshness_points: Double [0..50]",
            "- phone_validity_points: Double [0..25]",
            "- completeness_points: Double [0..25]",
            "- composite_score: Integer [0..100]",
            "- confidence_band: Enum(High/Med/Low)",
        ],
        ["+ calculate_trust_score(): Integer", "+ get_warning_notice(): String"],
        "#15803D",
    )

    # Class 4: EmergencyTriageEngine (Right)
    draw_class(
        9.8,
        5.0,
        3.6,
        3.6,
        "EmergencyTriageEngine",
        [
            "- patient_group: BloodGroupEnum",
            "- required_component: ComponentEnum",
            "- patient_lat: Double",
            "- patient_lon: Double",
            "- max_radius_km: Double",
        ],
        [
            "+ resolve_compatible_donors(): List",
            "+ calculate_triage_rank(fac): Double",
            "+ rank_top_facilities(limit=5): List",
            "+ generate_clinical_alerts(): List",
        ],
        "#BE123C",
    )

    # Class 5: DistrictShortageMart (Bottom Right)
    draw_class(
        7.0,
        0.8,
        4.2,
        3.2,
        "DistrictShortageMart (Aggregate)",
        [
            "- district_name: String [PK]",
            "- state_name: String",
            "- total_facilities: Integer",
            "- reporting_facilities: Integer",
            "- critical_deficits: List<String>",
            "- severe_shortage_flag: Boolean",
            "- last_audit_time: Timestamp",
        ],
        ["+ evaluate_deficit_severity(): Double", "+ export_to_excel_csv(): ByteStream"],
        "#C2410C",
    )

    # Associations & Connectors
    # BloodBank 1 --- * BloodComponent
    ax.annotate(
        "",
        xy=(5.5, 6.7),
        xytext=(4.6, 6.7),
        arrowprops=dict(arrowstyle="->", lw=1.5, color="#334155"),
    )
    ax.text(4.7, 6.9, "1", fontsize=8, fontweight="bold")
    ax.text(5.3, 6.9, "0..*", fontsize=8, fontweight="bold")
    ax.text(5.0, 6.4, "maintains", fontsize=7.5, fontstyle="italic", ha="center")

    # BloodBank 1 --- 1 ReliabilityScore
    ax.annotate(
        "",
        xy=(2.7, 4.0),
        xytext=(2.7, 4.8),
        arrowprops=dict(arrowstyle="->", lw=1.5, color="#334155"),
    )
    ax.text(2.9, 4.6, "1", fontsize=8, fontweight="bold")
    ax.text(2.9, 4.2, "1", fontsize=8, fontweight="bold")
    ax.text(2.0, 4.4, "audited by", fontsize=7.5, fontstyle="italic", ha="center")

    # EmergencyTriageEngine uses BloodBank & BloodComponent
    ax.annotate(
        "",
        xy=(9.1, 6.8),
        xytext=(9.8, 6.8),
        arrowprops=dict(arrowstyle="->", ls="--", lw=1.5, color="#BE123C"),
    )
    ax.text(9.45, 7.0, "queries", fontsize=7.5, fontstyle="italic", ha="center")

    # DistrictShortageMart aggregates BloodBank
    ax.annotate(
        "",
        xy=(4.6, 2.4),
        xytext=(7.0, 2.4),
        arrowprops=dict(arrowstyle="->", ls="--", lw=1.5, color="#C2410C"),
    )
    ax.text(5.8, 2.6, "aggregates", fontsize=7.5, fontstyle="italic", ha="center")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "class_diagram.png", bbox_inches="tight", dpi=300)
    plt.close()
    print("Class diagram generated.")


def create_activity_diagram():
    fig, ax = plt.subplots(figsize=(13, 11), dpi=300)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 11)
    ax.axis("off")

    # Title
    ax.text(
        6.5,
        10.6,
        "Raktsetu: UML Activity Diagram",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="#1A1214",
    )
    ax.text(
        6.5,
        10.25,
        "Smart Emergency Triage, Phenotype Safety & Multi-Criteria Ranking Workflow",
        ha="center",
        va="center",
        fontsize=10,
        fontstyle="italic",
        color="#555555",
    )

    def draw_node(x, y, w, h, text, bg="#E0F2FE", ec="#0284C7"):
        rect = patches.FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.15", ec=ec, fc=bg, lw=1.2
        )
        ax.add_patch(rect)
        ax.text(
            x, y, text, ha="center", va="center", fontsize=7.5, fontweight="bold", color="#0F172A"
        )

    def draw_decision(x, y, text):
        diamond = patches.Polygon(
            [[x, y + 0.45], [x + 1.1, y], [x, y - 0.45], [x - 1.1, y]],
            closed=True,
            ec="#D97706",
            fc="#FEF3C7",
            lw=1.2,
        )
        ax.add_patch(diamond)
        ax.text(
            x, y, text, ha="center", va="center", fontsize=7, fontweight="bold", color="#92400E"
        )

    # Initial State (Solid Circle)
    ax.plot(6.5, 9.6, "o", ms=16, mfc="#0F172A", mec="#0F172A")
    ax.annotate(
        "",
        xy=(6.5, 8.9),
        xytext=(6.5, 9.5),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#0F172A"),
    )

    # Step 1: User Selects Patient Blood Group & Component
    draw_node(
        6.5,
        8.5,
        4.4,
        0.7,
        "User Inputs Patient Blood Group\n& Desired Component Type",
        "#F1F5F9",
        "#475569",
    )
    ax.annotate(
        "",
        xy=(6.5, 7.8),
        xytext=(6.5, 8.15),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#0F172A"),
    )

    # Decision 1: Rare Blood Phenotype? (Bombay Oh / Rh-neg)
    draw_decision(6.5, 7.3, "Rare Phenotype\n(Oh or Rh-)?")

    # Yes branch -> Clinical Alert Triggered
    ax.annotate(
        "",
        xy=(3.0, 7.3),
        xytext=(5.4, 7.3),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#DC2626"),
    )
    ax.text(
        4.2, 7.5, "[Yes: Critical]", fontsize=7.5, fontweight="bold", color="#DC2626", ha="center"
    )
    draw_node(
        2.2, 7.3, 2.6, 0.7, "Flag Clinical Warning:\nStrict Rh/Oh Match Only", "#FEE2E2", "#DC2626"
    )

    # No branch -> Standard WHO Compatibility Resolution
    ax.annotate(
        "",
        xy=(6.5, 6.3),
        xytext=(6.5, 6.85),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#0F172A"),
    )
    ax.text(6.8, 6.6, "[Standard]", fontsize=7.5, color="#0F172A")

    # Step 2: Resolve Compatible Groups via WHO/NBTC Matrix
    draw_node(
        6.5,
        5.9,
        4.2,
        0.7,
        "Resolve Compatible Donor Groups\n(e.g., AB+ accepts all; O- donates to all)",
        "#FEF08A",
        "#CA8A04",
    )

    # Reconnect Rare branch to Step 2
    ax.annotate(
        "",
        xy=(4.4, 5.9),
        xytext=(2.2, 6.95),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#DC2626", connectionstyle="arc3,rad=-0.2"),
    )

    ax.annotate(
        "",
        xy=(6.5, 5.2),
        xytext=(6.5, 5.55),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#0F172A"),
    )

    # Decision 2: User Geolocation Available?
    draw_decision(6.5, 4.7, "Browser Location\nGranted?")

    # Geolocation Yes branch
    ax.annotate(
        "",
        xy=(9.8, 4.7),
        xytext=(7.6, 4.7),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#16A34A"),
    )
    ax.text(8.7, 4.9, "[Yes]", fontsize=7.5, fontweight="bold", color="#16A34A", ha="center")
    draw_node(
        10.6, 4.7, 2.4, 0.6, "Compute Exact Distance\nvia SQL Haversine", "#DCFCE7", "#16A34A"
    )

    # Geolocation No branch
    ax.annotate(
        "",
        xy=(6.5, 3.8),
        xytext=(6.5, 4.25),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#64748B"),
    )
    ax.text(6.8, 4.0, "[No / Fallback]", fontsize=7.5, color="#64748B")
    draw_node(
        6.5,
        3.4,
        3.8,
        0.6,
        "Fallback: District Centroid Coordinates\nwith Deterministic Non-Overlap",
        "#F1F5F9",
        "#64748B",
    )

    # Join paths to Query Execution
    draw_node(
        6.5,
        2.2,
        5.2,
        0.8,
        "Query DuckDB Lakehouse (gold.fct_stock_current)\nFilter Compatible Stock > 0 & Compute Triage Score:\nScore = 0.35F + 0.30T + 0.25U + 0.10D",
        "#E0F2FE",
        "#0284C7",
    )

    ax.annotate(
        "",
        xy=(6.5, 2.6),
        xytext=(6.5, 3.1),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#0F172A"),
    )
    ax.annotate(
        "",
        xy=(8.5, 2.6),
        xytext=(10.6, 4.4),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#16A34A", connectionstyle="arc3,rad=-0.2"),
    )

    ax.annotate(
        "",
        xy=(6.5, 1.5),
        xytext=(6.5, 1.8),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#0F172A"),
    )

    # Step 3: Rank & Present Top 5 Facilities
    draw_node(
        6.5,
        1.1,
        4.8,
        0.65,
        "Rank & Present Top 5 Verified Facilities\nWith Direct Click-to-Call & Navigation Action",
        "#FCE7F3",
        "#DB2777",
    )

    ax.annotate(
        "",
        xy=(6.5, 0.45),
        xytext=(6.5, 0.77),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#0F172A"),
    )

    # Final State (Bullseye)
    ax.plot(6.5, 0.3, "o", ms=16, mfc="none", mec="#0F172A", mew=2)
    ax.plot(6.5, 0.3, "o", ms=10, mfc="#0F172A", mec="#0F172A")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "activity_diagram.png", bbox_inches="tight", dpi=300)
    plt.close()
    print("Activity diagram generated.")


def create_sequence_diagram():
    fig, ax = plt.subplots(figsize=(14, 9), dpi=300)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # Title
    ax.text(
        7,
        8.6,
        "Raktsetu: UML Sequence Diagram (Emergency Triage Flow)",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color="#1A1214",
    )
    ax.text(
        7,
        8.25,
        "Interaction Lifecycle: Requester -> Browser UI -> FastAPI -> Medical Rules -> DuckDB",
        ha="center",
        va="center",
        fontsize=9.5,
        fontstyle="italic",
        color="#555555",
    )

    lifelines = [
        (1.5, "Emergency Requester\n(User/Caregiver)", "#E2E8F0"),
        (4.2, "Clinical Web UI\n(Vanilla JS / Leaflet)", "#FEE2E2"),
        (7.2, "FastAPI Backend\n(/api/v1/emergency)", "#E0F2FE"),
        (10.0, "Medical Rule Engine\n(NBTC/WHO Rules)", "#FEF3C7"),
        (12.5, "DuckDB Lakehouse\n(serving.duckdb)", "#DCFCE7"),
    ]

    for x, label, bg in lifelines:
        # Box header
        rect = patches.FancyBboxPatch(
            (x - 1.1, 7.3), 2.2, 0.7, boxstyle="round,pad=0.1", ec="#334155", fc=bg, lw=1.2
        )
        ax.add_patch(rect)
        ax.text(
            x,
            7.65,
            label,
            ha="center",
            va="center",
            fontsize=7.5,
            fontweight="bold",
            color="#0F172A",
        )
        # Dashed line
        ax.plot([x, x], [1.0, 7.3], color="#94A3B8", lw=1.2, ls="--")

    # Sequence Messages
    steps = [
        (6.7, 1.5, 4.2, '1. Selects B+ Whole Blood & clicks "Emergency Mode"', "->", "#0F172A"),
        (
            6.1,
            4.2,
            7.2,
            '2. POST /api/v1/emergency {group:"B+", component:"WB", lat, lon}',
            "->",
            "#BE123C",
        ),
        (5.5, 7.2, 10.0, '3. resolve_compatible_groups("B+", "WB")', "->", "#D97706"),
        (4.9, 10.0, 7.2, '4. Returns compatible list: ["B+", "B-", "O+", "O-"]', "-->", "#D97706"),
        (
            4.3,
            7.2,
            12.5,
            "5. SQL Query: fct_stock_current WHERE group IN (...) & calc distance",
            "->",
            "#0284C7",
        ),
        (
            3.7,
            12.5,
            7.2,
            "6. Returns matching facilities with trust scores & units",
            "-->",
            "#0284C7",
        ),
        (
            3.1,
            7.2,
            7.2,
            "7. Calculate Triage Score: 0.35F + 0.30T + 0.25U + 0.10D",
            "loop",
            "#4338CA",
        ),
        (
            2.5,
            7.2,
            4.2,
            "8. JSON Response: Top 5 ranked facilities with breakdown",
            "-->",
            "#BE123C",
        ),
        (
            1.9,
            4.2,
            1.5,
            "9. Renders Verified Facility Cards, Map Pins & One-Click Call",
            "-->",
            "#0F172A",
        ),
        (1.3, 1.5, 1.5, "10. Clicks Direct Phone Dial to confirm bed-side hold", "self", "#15803D"),
    ]

    for y, x1, x2, msg, style, col in steps:
        if style == "->":
            ax.annotate(
                "", xy=(x2, y), xytext=(x1, y), arrowprops=dict(arrowstyle="-|>", lw=1.4, color=col)
            )
            ax.text(
                (x1 + x2) / 2,
                y + 0.15,
                msg,
                ha="center",
                fontsize=7.5,
                fontweight="bold",
                color=col,
            )
        elif style == "-->":
            ax.annotate(
                "",
                xy=(x2, y),
                xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", ls="--", lw=1.4, color=col),
            )
            ax.text(
                (x1 + x2) / 2,
                y + 0.15,
                msg,
                ha="center",
                fontsize=7.5,
                fontstyle="italic",
                color=col,
            )
        elif style == "loop":
            rect = patches.FancyBboxPatch(
                (x1 - 0.2, y - 0.2), 2.2, 0.4, boxstyle="round,pad=0.05", ec=col, fc="#EEF2FF", lw=1
            )
            ax.add_patch(rect)
            ax.text(
                x1 + 0.9,
                y,
                msg,
                ha="center",
                va="center",
                fontsize=6.8,
                fontweight="bold",
                color=col,
            )
        elif style == "self":
            ax.annotate(
                "",
                xy=(x1 + 0.5, y - 0.2),
                xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", lw=1.2, color=col),
            )
            ax.plot([x1, x1 + 0.5, x1 + 0.5], [y, y, y - 0.2], color=col, lw=1.2)
            ax.text(
                x1 + 0.6,
                y - 0.1,
                msg,
                ha="left",
                va="center",
                fontsize=7.2,
                fontweight="bold",
                color=col,
            )

    plt.tight_layout()
    plt.savefig(OUT_DIR / "sequence_diagram.png", bbox_inches="tight", dpi=300)
    plt.close()
    print("Sequence diagram generated.")


if __name__ == "__main__":
    create_system_architecture()
    create_use_case_diagram()
    create_class_diagram()
    create_activity_diagram()
    create_sequence_diagram()
    print("All 5 diagrams successfully generated at high resolution (300 DPI).")
