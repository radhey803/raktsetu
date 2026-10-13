# Hemolytics: Smart Blood Inventory & Logistics Platform
**A Data Engineering & Full-Stack Project Proposal**

This document outlines the complete feature set and technical architecture for a modern, data-driven blood bank management and logistics platform. The data is powered by a custom scraping pipeline that extracts live data from the government eRaktKosh portal.

---

## 🚀 1. Standard Features (Core Requirements)
*These are the foundational features expected in any blood bank portal (similar to what eRaktKosh currently provides).*

*   **Real-Time Inventory Search:** Users can search for current blood availability by State, District, Blood Group (A+, O-, etc.), and Component (Whole Blood, Plasma, Platelets).
*   **Blood Bank Directory:** A comprehensive, searchable directory of all hospitals and blood banks, including contact numbers, addresses, and operating hours.
*   **Donation Camp Locator:** A calendar and search tool for finding upcoming blood donation camps in specific regions.
*   **Basic Donor Registration:** A portal for donors to register their blood type, location, and contact information for future donations.

---

## 🌟 2. Unique & Advanced Features (The Project Differentiators)
*These features rely on advanced Data Engineering and solve real-world problems that official portals currently ignore. These will make your portfolio stand out.*

*   **Predictive Blood Shortage AI (Demand Forecasting):** 
    *   *How it works:* Because the data pipeline scrapes and stores inventory data every few hours, the system builds historical trends. A forecasting algorithm predicts which hospitals are likely to run out of specific blood types in the next 3-7 days.
*   **Smart Logistics & Routing Engine (Wastage Prevention):** 
    *   *How it works:* An algorithm that detects when Hospital A has a critical shortage of a blood type, while Hospital B (nearby) has a surplus or units nearing expiration. The system automatically recommends a transfer route to balance the inventory and prevent wastage.
*   **Geofenced Automated Donor Alerts (SOS System):** 
    *   *How it works:* When the pipeline detects a sudden drop in a specific blood type in a specific pincode, it automatically triggers an SMS (Twilio) or Email (AWS SES) to registered donors of that exact blood type who live within a 10km radius.
*   **Interactive Heatmap Dashboard:** 
    *   *How it works:* Instead of manual dropdown searches, administrators view a live geographic heatmap (using Mapbox/Leaflet). Red zones indicate critical shortages, green zones indicate healthy supply, allowing for instant visual assessment of regional health.
*   **"Data as a Service" (DaaS) Public API:** 
    *   *How it works:* The backend provides a clean, documented REST or GraphQL API. This allows other developers, researchers, or mobile app creators to query your database for blood availability, turning your project into a centralized data hub.
*   **Gamified Donor Engagement (Leaderboards):** 
    *   *How it works:* Donors earn points for donating or responding to SOS alerts. The UI features community or city-wide leaderboards (e.g., "Top Donors in Delhi this month") and tracks a personal "Lives Saved" metric.

---

## ⚙️ 3. Data Engineering Architecture & Tech Stack

### Pipeline Phases:
1.  **Extraction (Scraping):** 
    *   **Tool:** Node.js Puppeteer or Python Playwright.
    *   **Function:** Runs in a headless browser to bypass dynamic React rendering and API obfuscation on eRaktKosh, extracting the raw inventory tables.
2.  **Orchestration:** 
    *   **Tool:** Apache Airflow or GitHub Actions.
    *   **Function:** Schedules the scraper to run automatically every 4 to 6 hours to keep the data fresh without overloading servers.
3.  **Storage:** 
    *   **Raw Data Lake:** AWS S3 (Stores raw JSON/CSV dumps).
    *   **Data Warehouse/Database:** PostgreSQL (Stores clean, queryable data for the application).
4.  **Transformation:** 
    *   **Tool:** dbt (Data Build Tool) or Python (Pandas).
    *   **Function:** Cleans the raw scraped data and structures it into Fact (inventory logs) and Dimension (hospital details) tables.

### Full-Stack Application:
*   **Backend API:** FastAPI (Python) or Node.js (Express). Extremely fast for serving data to the frontend and handling the Public API.
*   **Frontend UI:** Next.js (React) styled with Tailwind CSS for a premium, dark-mode, responsive user experience.
*   **Data Visualization:** Recharts or Chart.js for forecasting graphs, and Mapbox for the logistics map.
