# Documentation

## For developers

| Document | What it covers |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, medallion layers, publish gate |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Every bronze / silver / gold table and column |
| [API.md](API.md) | REST endpoints with request/response examples |
| [FEATURES.md](FEATURES.md) | How each user-facing feature works end to end |
| [TESTING.md](TESTING.md) | Test strategy and how to run the suites |
| [adr/](adr/) | Architecture Decision Records (why DuckDB, dbt incremental design, etc.) |

## For users and evaluators

| Document | What it covers |
|---|---|
| [USER_MANUAL.md](USER_MANUAL.md) | Running the app and using each screen |
| [../demo/README.md](../demo/README.md) | Offline demo procedure |

## Academic submission

| Document | What it covers |
|---|---|
| [academic/REPORT.md](academic/REPORT.md) | Project report (Markdown source) |
| [academic/PRESENTATION_OUTLINE.md](academic/PRESENTATION_OUTLINE.md) | Slide outline and demo script |
| [academic/VIVA_QA.md](academic/VIVA_QA.md) | Viva questions and answers |
| [academic/FINAL_CHECK.md](academic/FINAL_CHECK.md), [academic/FEATURES_CHECK.md](academic/FEATURES_CHECK.md) | Submission checklists |
| [../reports/](../reports/) | Final `.docx` / `.pdf` report |

## Assets

- [diagrams/](diagrams/): architecture and UML diagrams, regenerated with `make diagrams`
- [screenshots/](screenshots/): UI screenshots embedded in the report
- [learning/](learning/): DuckDB and dbt study notes (background reading, not project docs)

The `.docx` report is built by `scripts/report/build_raktsetu_docx.py` (`make report`).
