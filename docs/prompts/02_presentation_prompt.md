# Prompt: Build the Raktsetu Project Presentation (12 slides)

> Copy everything below the line into an AI assistant that can create PowerPoint files and read this repo.

---

## Role and goal

You are a presentation designer and a final-year MCA project mentor. Create a **12-slide PowerPoint deck
(`reports/Raktsetu_Presentation.pptx`)** for presenting the project **Raktsetu** to internal faculty at
CMPICA, CHARUSAT. The talk is **10–12 minutes**, followed by a viva.

- **Presenters:** Radhey Gajera (25MCA057) and Shruti Gajipara (25MCA058)
- **Guide:** Ms. Konica Soni

## Sources (read these first; use only facts from them)

- `reports/Raktsetu_Project_Report.pdf`: the full report. Use it for the abstract, features, test numbers,
  limitations and future scope.
- `README.md`, `docs/ARCHITECTURE.md`, `docs/FEATURES.md`, `docs/academic/PRESENTATION_OUTLINE.md`,
  `docs/academic/VIVA_QA.md`
- Images:
  - `docs/diagrams/`: architecture, use case, DFD, ER and activity diagrams
  - `docs/screenshots/`: desktop and mobile screens
  - `scripts/report/assets/`: CHARUSAT and CMPICA logos

Don't invent numbers. Take counts (blood banks, districts, tests) from the report or the live data.

## Design rules

- 16:9 layout. Clean, light theme with one accent colour: blood red `#B71C1C`. Dark grey text `#212121`.
  A soft background `#FAFAFA`.
- Fonts: titles in Poppins or Segoe UI Semibold, 32–36 pt. Body text 18–22 pt, **never below 16 pt**.
- **At most 5 bullets per slide and about 8 words per bullet.** Prefer visuals over text.
- Every slide has:
  - a title that states the point (for example "Data refreshes automatically every few hours", not "Pipeline");
  - a small footer: `Raktsetu | CMPICA, CHARUSAT` and the slide number.
- Diagrams and screenshots must be large and readable. Crop the screenshots to the relevant part.
- Use simple icons, the same style throughout. No clip-art and no heavy animation; simple fade at most.
- Add **speaker notes** to every slide: 60–90 seconds of simple spoken English. Mark which presenter speaks
  (split the slides about 50/50).

## Slide plan

1. **Title:**
   - Raktsetu: Real-Time Blood Availability Finder
   - the subtitle (Lakehouse + PWA)
   - the names, roll numbers, guide, institute logos and month/year
2. **The problem:** finding blood in an emergency means calling many banks. eRaktKosh has the data but it is
   hard to search. Use one strong statistic or story and a simple "before" illustration.
3. **Our solution, in one line plus 3 points:** collect automatically, check the quality, search instantly
   on any phone. Add a hero screenshot.
4. **Who uses it (use case):** the use case diagram, with the actors explained in one line each (Patient's
   Family, Doctor/Staff, Health Official, Blood Donor, Operator, plus system actors).
5. **Key features:** a 2×3 grid of icon + name + one line (Blood Finder, Emergency Mode, Map/Near Me,
   Trust Score, Shortage Alerts/Rare Radar, CSV Export/Donor Check/Offline PWA).
6. **Live demo screens:** 3–4 screenshots (finder, emergency, map, mobile) with callouts.
   Note in the speaker notes: "switch to live demo here (2 min)".
7. **System architecture:** the architecture diagram, with the flow scraper → Parquet → DuckDB bronze →
   dbt silver/gold → quality gate → serving DB → FastAPI → PWA. One line on why it is layered
   (raw data is kept, checked, then published safely).
8. **Technology stack:** grouped logos/labels: Data (Python, aiohttp, Parquet, DuckDB, dbt), Backend
   (FastAPI, Pydantic), Frontend (HTML/CSS/JS, Leaflet, Chart.js, PWA), DevOps (GitHub Actions, Docker,
   pytest, Playwright). Add one "why" for the main choices (DuckDB: fast analytics with no server).
9. **Data quality and reliability:** the quality gate, dbt tests, trust score and freshness. Show how the
   trust score is calculated, with a small worked example.
10. **Testing and results:** a numbers row: pytest, dbt tests, Playwright checks, devices/widths tested
    (from the report). Add the performance or coverage facts that are in the report.
11. **Limitations and future scope:** two columns. Limitations as stated in the report. Future scope with
    4–5 items (for example SMS/WhatsApp alerts, donor registration, hospital login for direct updates,
    demand forecasting, regional languages).
12. **Conclusion and thank you:** 3 takeaways (impact, technical learning, a working product), the
    GitHub/demo link placeholder and "Questions?".

**Optional backup slides** (after "Thank you", hidden): ER diagram, DFD Level 1, sequence diagram, API list,
and 6 likely viva questions with short answers.

## Output and checks

- Build the deck with `python-pptx` (or the available pptx tool). Embed the images; do not link them.
- Render every slide to an image and **look at each one**. Fix any text overflow, overlap, or font under
  16 pt, and any diagram that is not readable.
- Also export `reports/Raktsetu_Presentation.pdf`.
- Finish with a list of the slides (title + the image used) and the facts you could not verify.
