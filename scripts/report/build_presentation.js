const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("/home/radhey/.claude/skills/synced/8dd510ca-6978-4b27-8d10-debc1415192f_5e729417-52fe-4c1b-aa02-29edb9f751f3/pptx/scripts/apply_theme.js");

const ROOT = "/home/radhey/Documents/project_idea/";
const IMG = __dirname + "/img/";
const OUT = ROOT + "reports/Raktsetu_Presentation.pptx";

const THEME = {
  name: "Raktsetu",
  headFontFace: "Segoe UI Semibold",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "212121", lt1: "FFFFFF", dk2: "5F0F0F", lt2: "FAFAFA",
    accent1: "B71C1C", accent2: "FDECEA", accent3: "546E7A", accent4: "EEEEEE",
    accent5: "2E7D32", accent6: "F9A825", hlink: "B71C1C", folHlink: "7F1010",
  },
};
const HEX = { red: "B71C1C", ink: "212121", white: "FFFFFF", slate: "546E7A" };

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.title = "Raktsetu: Real-Time Blood Availability Finder";
  pres.author = "Radhey Gajera, Shruti Gajipara";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const W = 13.333;

  const footer = (dark) => [
    { text: { text: "Raktsetu | CMPICA, CHARUSAT", options: { x: 0.6, y: 6.95, w: 6, h: 0.35, fontSize: 12, color: dark ? C.background2 : C.accent3, margin: 0 } } },
  ];
  const num = (dark) => ({ x: 12.1, y: 6.95, w: 0.63, h: 0.35, fontSize: 12, color: dark ? C.background2 : C.accent3, align: "right" });

  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: C.background2 },
    objects: [
      ...footer(false),
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.13, h: 0.95, fontSize: 30, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    ],
    slideNumber: num(false),
  });
  pres.defineSlideMaster({
    title: "DARK",
    background: { color: C.text2 },
    objects: [...footer(true)],
    slideNumber: num(true),
  });

  const I = {};
  for (const [k, comp] of Object.entries({
    phone: fa.FaPhoneAlt, clock: fa.FaRegClock, search: fa.FaSearchMinus, collect: fa.FaCloudDownloadAlt,
    check: fa.FaShieldAlt, mobile: fa.FaMobileAlt, finder: fa.FaSearch, amb: fa.FaAmbulance, map: fa.FaMapMarkedAlt,
    trust: fa.FaStar, rare: fa.FaExclamationTriangle, csv: fa.FaFileCsv, fam: fa.FaUsers, doc: fa.FaUserMd,
    off: fa.FaChartBar, donor: fa.FaHandHoldingHeart, op: fa.FaCogs, drop: fa.FaTint,
  })) I[k] = await icon(comp, HEX.white);
  const iconRed = {};
  for (const [k, comp] of Object.entries({ drop: fa.FaTint, ok: fa.FaCheckCircle, limit: fa.FaMinusCircle, plus: fa.FaPlusCircle }))
    iconRed[k] = await icon(comp, HEX.red);

  // icon inside a red circle (the deck's motif)
  const dot = (s, img, x, y, d = 0.62, name = "icon") => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: name + " circle" });
    s.addImage({ data: img, x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, objectName: name });
  };
  const card = (s, x, y, w, h, name) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: C.background1 },
      line: { color: C.accent4, width: 1 }, shadow: { type: "outer", blur: 6, offset: 2, angle: 90, color: "000000", opacity: 0.12 }, objectName: name });
  const txt = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontSize: 18, color: C.text1, valign: "top", ...o });
  const shot = (s, file, x, y, w, h, name) => {
    s.addImage({ path: file, x, y, w, h, objectName: name });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { type: "none" }, line: { color: "BDBDBD", width: 1 }, objectName: name + " frame" });
  };
  const content = (section, title) => {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
    s.addText(title, { placeholder: "title" });
    return s;
  };

  // ---------- 1. Title ----------
  pres.addSection({ title: "Introduction" });
  let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Introduction" });
  dot(s, I.drop, 0.8, 0.9, 0.9, "drop icon");
  txt(s, "Raktsetu", { x: 0.8, y: 2.0, w: 7.5, h: 1.1, fontSize: 54, bold: true, color: C.background1, fontFace: THEME.headFontFace });
  txt(s, "Real-Time Blood Availability Finder", { x: 0.8, y: 3.1, w: 7.5, h: 0.6, fontSize: 26, color: C.background1 });
  txt(s, "A Medallion Lakehouse + Progressive Web App", { x: 0.8, y: 3.7, w: 7.5, h: 0.5, fontSize: 20, italic: true, color: C.accent2 });
  txt(s, [
    { text: "Radhey Gajera (25MCA057)  ·  Shruti Gajipara (25MCA058)", options: { breakLine: true } },
    { text: "Guide: Ms. Konica Soni  ·  November 2026" },
  ], { x: 0.8, y: 4.8, w: 7.8, h: 0.9, fontSize: 18, color: C.background1, paraSpaceAfter: 6 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.0, y: 2.0, w: 3.6, h: 3.4, rectRadius: 0.15, fill: { color: C.background1 }, line: { color: C.background1 }, objectName: "logo card" });
  s.addImage({ path: ROOT + "scripts/report/assets/cmpica_logo.jpeg", x: 10.12, y: 2.25, w: 1.36, h: 1.49, objectName: "CMPICA logo" });
  s.addImage({ path: ROOT + "scripts/report/assets/charusat_logo.jpeg", x: 9.25, y: 4.15, w: 3.1, h: 0.61, objectName: "CHARUSAT logo" });
  txt(s, "MCA Project · CMPICA, CHARUSAT", { x: 9.0, y: 5.6, w: 3.6, h: 0.4, fontSize: 14, color: C.accent2, align: "center" });
  s.addNotes("[Radhey] Good morning, respected faculty. I am Radhey Gajera, and with me is Shruti Gajipara. Our project is Raktsetu, which means 'bridge of blood'. It is a real-time blood availability finder for all of India. It collects blood stock data from the government's eRaktKosh portal every few hours, checks its quality, and shows it on a fast website that works on any phone, even offline. Our guide is Ms. Konica Soni. In the next ten minutes we will show the problem, our solution, how it is built, how we tested it, and a short live demo.");

  // ---------- 2. Problem ----------
  s = content("Introduction", "In an emergency, families still phone bank after bank");
  const pains = [
    [I.phone, "Search one district at a time", "eRaktKosh has the data, but it is slow to search on a phone"],
    [I.search, "No compatible-group search", "An O- patient can only take O-; the portal does not show this"],
    [I.clock, "No sign of how fresh data is", "Some banks have not updated for weeks"],
  ];
  pains.forEach(([ic, h, d], i) => {
    const y = 1.75 + i * 1.5;
    dot(s, ic, 0.7, y, 0.75, "pain icon " + (i + 1));
    txt(s, h, { x: 1.7, y, w: 5.9, h: 0.45, fontSize: 22, bold: true });
    txt(s, d, { x: 1.7, y: y + 0.48, w: 5.9, h: 0.75, fontSize: 18, color: C.accent3 });
  });
  card(s, 8.1, 1.75, 4.6, 4.4, "stat card");
  txt(s, "4,716", { x: 8.4, y: 2.05, w: 4.0, h: 1.0, fontSize: 60, bold: true, color: C.accent1, align: "center", fontFace: THEME.headFontFace });
  txt(s, "blood banks on eRaktKosh", { x: 8.4, y: 3.05, w: 4.0, h: 0.45, align: "center" });
  txt(s, "701", { x: 8.4, y: 3.7, w: 4.0, h: 1.0, fontSize: 60, bold: true, color: C.accent1, align: "center", fontFace: THEME.headFontFace });
  txt(s, "districts in 35 states / UTs", { x: 8.4, y: 4.7, w: 4.0, h: 0.45, align: "center" });
  txt(s, "…and every minute counts", { x: 8.4, y: 5.4, w: 4.0, h: 0.45, align: "center", italic: true, color: C.accent3 });
  s.addNotes("[Radhey] Imagine a patient needs O-negative blood at night. The family opens eRaktKosh, picks one district, checks it, then the next district, and keeps phoning banks. The data exists: our database has 4,716 blood banks in 701 districts across 35 states and union territories. But the portal makes you search district by district, it does not tell you which groups are compatible, and it does not warn you when a bank has not updated its stock for weeks. In an emergency, these minutes matter. That is the gap we wanted to close.");

  // ---------- 3. Solution ----------
  s = content("Introduction", "One pipeline collects, checks and serves India's blood stock");
  const steps = [
    [I.collect, "Collect automatically", "Polite crawler fetches every district every 6 hours"],
    [I.check, "Check the quality", "37 data tests and a safety gate block bad data"],
    [I.mobile, "Search instantly on any phone", "Fast, installable web app that also works offline"],
  ];
  steps.forEach(([ic, h, d], i) => {
    const y = 1.75 + i * 1.55;
    dot(s, ic, 0.7, y, 0.75, "step icon " + (i + 1));
    txt(s, h, { x: 1.7, y, w: 4.7, h: 0.45, fontSize: 22, bold: true });
    txt(s, d, { x: 1.7, y: y + 0.48, w: 4.7, h: 0.8, fontSize: 18, color: C.accent3 });
  });
  shot(s, IMG + "hero.jpg", 6.75, 1.6, 5.98, 3.74, "home screenshot");
  txt(s, "Home page: live counts of fresh and stale blood banks", { x: 6.75, y: 5.45, w: 5.98, h: 0.4, fontSize: 14, color: C.accent3, italic: true });
  s.addNotes("[Radhey] Our solution does three things. First, it collects data automatically: a polite crawler visits every district on eRaktKosh every six hours. Second, it checks the quality: 37 automatic data tests and a safety gate make sure broken data never reaches users. Third, it lets anyone search instantly from any phone. On the right is the home page. It shows how many banks updated in the last 24 hours and how many are stale, so users know how much to trust the numbers.");

  // ---------- 4. Use case ----------
  pres.addSection({ title: "Product" });
  s = content("Product", "Five kinds of people use Raktsetu for different needs");
  s.addImage({ path: ROOT + "docs/diagrams/use_case_diagram.png", x: 0.6, y: 1.45, w: 5.4, h: 5.29, objectName: "use case diagram" });
  const actors = [
    [I.fam, "Patient's family", "Find nearby stock and call the bank"],
    [I.doc, "Doctor / hospital staff", "Emergency Mode: compatible, ranked banks"],
    [I.off, "Health official", "District shortages, rare blood, CSV export"],
    [I.donor, "Blood donor", "Check eligibility, see where stock is low"],
    [I.op, "Operator", "Runs the pipeline and watches data health"],
  ];
  actors.forEach(([ic, h, d], i) => {
    const y = 1.5 + i * 0.98;
    dot(s, ic, 6.5, y, 0.6, "actor icon " + (i + 1));
    txt(s, h, { x: 7.3, y: y - 0.04, w: 5.4, h: 0.38, fontSize: 19, bold: true });
    txt(s, d, { x: 7.3, y: y + 0.34, w: 5.4, h: 0.38, fontSize: 16, color: C.accent3 });
  });
  txt(s, "System actors: eRaktKosh portal, Device GPS, OpenStreetMap", { x: 6.5, y: 6.4, w: 6.2, h: 0.35, fontSize: 16, italic: true, color: C.accent1 });
  s.addNotes("[Radhey] Who uses Raktsetu? We identified five human roles. The patient's family searches nearby stock and calls the bank. Doctors and hospital staff use Emergency Mode to get compatible, ranked blood banks. Health officials look at district shortages and rare blood, and export CSV files. Blood donors check if they are eligible and see where stock is low. Finally, the operator runs the data pipeline. There are also three system actors: the eRaktKosh portal as our data source, the device GPS for 'near me', and OpenStreetMap for district locations.");

  // ---------- 5. Features ----------
  s = content("Product", "Six features turn raw stock data into fast decisions");
  const feats = [
    [I.finder, "Blood Finder", "State, district, group and component filters with sorting"],
    [I.amb, "Emergency Mode", "Compatible groups, ranked by freshness, trust and distance"],
    [I.map, "Map + Near Me", "Banks on a map; GPS search widens 50 → 150 → 400 km"],
    [I.trust, "Trust Score", "0–100 score from freshness, phone and coverage"],
    [I.rare, "Shortages + Rare Radar", "Districts running out; where Rh-negative and Bombay are"],
    [I.csv, "Export, Donor Check, Offline", "Excel-safe CSV, eligibility checker, works without internet"],
  ];
  feats.forEach(([ic, h, d], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.6 + col * 4.1, y = 1.55 + row * 2.6;
    card(s, x, y, 3.85, 2.35, "feature card " + (i + 1));
    dot(s, ic, x + 0.3, y + 0.3, 0.65, "feature icon " + (i + 1));
    txt(s, h, { x: x + 1.1, y: y + 0.4, w: 2.6, h: 0.5, fontSize: 20, bold: true });
    txt(s, d, { x: x + 0.3, y: y + 1.15, w: 3.3, h: 1.0, fontSize: 16, color: C.accent3 });
  });
  s.addNotes("[Shruti] Thank you, Radhey. I am Shruti, and I will cover the features. The Blood Finder filters by state, district, blood group and component. Emergency Mode is the heart of the project: it knows which groups are compatible and ranks banks by freshness, trust and distance. The map shows every bank, and 'Near me' widens the search from 50 to 150 to 400 kilometres until it finds stock. Every bank gets a trust score. Officials see district shortages and a rare blood radar. We also have Excel-safe CSV export, a donor eligibility checker, and offline support.");

  // ---------- 6. Demo ----------
  s = content("Product", "The same app works on a desktop and a phone");
  shot(s, IMG + "emergency.jpg", 0.6, 1.55, 4.67, 4.1, "emergency screenshot");
  shot(s, IMG + "map.jpg", 5.66, 1.55, 4.63, 4.1, "map screenshot");
  shot(s, IMG + "mobile.jpg", 10.68, 1.55, 2.05, 4.1, "mobile screenshot");
  const caps = [[0.6, 4.67, "Emergency Mode: ranked banks, each with a reason"], [5.66, 4.63, "Map view: click a pin to see and call"], [10.68, 2.05, "Phone view"]];
  caps.forEach(([x, w, t]) => txt(s, t, { x, y: 5.8, w, h: 0.7, fontSize: 15, color: C.accent3 }));
  s.addNotes("[Shruti] Here are three real screens. On the left, Emergency Mode for an O-negative patient. Each card shows compatible units, how fresh the data is, the trust score, and one line explaining why it is ranked there, with a call button. In the middle is the map view; clicking a pin shows the bank and its phone number. On the right is the same emergency search on a phone. Switch to live demo here (2 min): search Gujarat, Anand; run Emergency Mode for O-; open the map; open a trend chart.");

  // ---------- 7. Architecture ----------
  pres.addSection({ title: "How it works" });
  s = content("How it works", "Data is kept raw, checked, then published safely");
  const flow = ["Scraper\n(aiohttp)", "Parquet\nlanding", "DuckDB\nbronze", "dbt silver\n+ gold", "Quality\ngate", "serving\n.duckdb", "FastAPI", "Web app\n(PWA)"];
  flow.forEach((t, i) => {
    const row = Math.floor(i / 4), col = row === 0 ? i % 4 : 3 - (i % 4);
    const x = 0.6 + col * 3.15, y = 1.7 + row * 2.05;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.55, h: 1.2, rectRadius: 0.12, fill: { color: i === 4 ? C.accent1 : C.background1 },
      line: { color: C.accent1, width: 1.5 }, objectName: "flow step " + (i + 1) });
    s.addText(t, { isTextBox: true, x, y, w: 2.55, h: 1.2, margin: 0, align: "center", valign: "middle", fontSize: 18, bold: true, color: i === 4 ? C.background1 : C.text1 });
    if (i === 3) s.addShape(pres.shapes.LINE, { x: x + 1.275, y: y + 1.2, w: 0, h: 0.85, line: { color: C.accent3, width: 2, endArrowType: "triangle" }, objectName: "arrow down" });
    else if (i < 7) {
      const ax = row === 0 ? x + 2.55 : x - 0.6;
      s.addShape(pres.shapes.LINE, { x: ax, y: y + 0.6, w: 0.6, h: 0, flipH: row === 1, line: { color: C.accent3, width: 2, endArrowType: "triangle" }, objectName: "arrow " + (i + 1) });
    }
  });
  card(s, 0.6, 5.35, 12.13, 1.3, "why card");
  txt(s, [
    { text: "Why layers? ", options: { bold: true, color: C.accent1 } },
    { text: "Raw files are never changed, so any table can be rebuilt. If a scrape is bad (banks drop below 80% of the last run), publishing stops and users keep yesterday's good data." },
  ], { x: 0.9, y: 5.5, w: 11.6, h: 1.0, valign: "middle" });
  s.addNotes("[Shruti] This is the architecture. The scraper fetches every district and saves the raw answer as a Parquet file that is never changed. We load it into DuckDB as the bronze layer. dbt then cleans it into silver tables and builds gold tables, such as current stock, trust score and shortages. A quality gate checks the result. If the number of banks falls below 80 percent of the last run, we stop. Only good data is copied, in one atomic step, into the serving database. FastAPI reads that and the web app shows it. Layers mean we can always rebuild from raw data and never show half-broken data.");

  // ---------- 8. Tech stack ----------
  s = content("How it works", "A free, open-source stack that runs on one small server");
  const stack = [
    ["Data", ["Python 3.12", "aiohttp (async)", "Parquet", "DuckDB", "dbt"]],
    ["Backend", ["FastAPI", "Pydantic", "Uvicorn", "Typer CLI"]],
    ["Frontend", ["HTML, CSS, JavaScript", "Leaflet + CARTO", "Chart.js", "PWA (service worker)"]],
    ["DevOps & testing", ["GitHub Actions", "Docker", "pytest", "Playwright", "ruff"]],
  ];
  stack.forEach(([h, items], i) => {
    const x = 0.6 + i * 3.08;
    card(s, x, 1.5, 2.85, 3.75, "stack card " + (i + 1));
    txt(s, h, { x: x + 0.25, y: 1.7, w: 2.4, h: 0.45, fontSize: 21, bold: true, color: C.accent1 });
    txt(s, items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } })),
      { x: x + 0.25, y: 2.3, w: 2.45, h: 2.8, fontSize: 17, paraSpaceAfter: 6 });
  });
  txt(s, [
    { text: "DuckDB: ", options: { bold: true } }, { text: "fast analytics in a single file, no database server.   ", options: {} },
    { text: "dbt: ", options: { bold: true } }, { text: "readable SQL with built-in tests.   ", options: {} },
    { text: "FastAPI: ", options: { bold: true } }, { text: "validation and API docs for free." },
  ], { x: 0.6, y: 5.55, w: 12.13, h: 0.9, fontSize: 17, valign: "middle" });
  s.addNotes("[Shruti] Everything we used is free and open source. For data: Python with aiohttp for fast asynchronous scraping, Parquet files, DuckDB and dbt. The backend is FastAPI with Pydantic validation. The frontend is plain HTML, CSS and JavaScript, with Leaflet maps and Chart.js, and it is a progressive web app. For quality we use pytest, Playwright, ruff and GitHub Actions, and Docker to deploy. We chose DuckDB because it is very fast for analytics and is just a file, with no server to manage. dbt gives us readable SQL with tests built in.");

  // ---------- 9. Data quality ----------
  s = content("How it works", "Every number is checked; every bank gets a trust score");
  const gates = [
    ["Circuit breaker", "Scrape stops if more than 20% of requests fail"],
    ["37 dbt data tests", "No missing keys, no duplicates, valid blood groups"],
    ["Anomaly gate", "Publish blocked if banks fall below 80% of last run"],
    ["Freshness shown", "Every card says when the bank last updated"],
  ];
  gates.forEach(([h, d], i) => {
    const y = 1.6 + i * 1.22;
    s.addImage({ data: iconRed.ok, x: 0.6, y: y + 0.05, w: 0.45, h: 0.45, objectName: "check icon " + (i + 1) });
    txt(s, h, { x: 1.25, y, w: 5.0, h: 0.42, fontSize: 21, bold: true });
    txt(s, d, { x: 1.25, y: y + 0.44, w: 5.0, h: 0.6, fontSize: 17, color: C.accent3 });
  });
  card(s, 6.75, 1.55, 5.98, 4.6, "trust card");
  txt(s, "Trust score, worked example", { x: 7.05, y: 1.75, w: 5.4, h: 0.45, fontSize: 21, bold: true, color: C.accent1 });
  const rowsT = [
    ["Part", "Rule", "Points"],
    ["Freshness", "Updated 2 days ago", "35 / 50"],
    ["Valid phone", "8 or more digits", "25 / 25"],
    ["Components", "4 types reported", "25 / 25"],
    ["Total", "High (75 or more)", "85 / 100"],
  ].map((r, i) => r.map((c) => ({ text: c, options: { bold: i === 0 || i === 4, color: i === 0 ? C.background1 : C.text1, fill: { color: i === 0 ? C.accent1 : i === 4 ? C.accent2 : C.background1 } } })));
  s.addTable(rowsT, { x: 7.05, y: 2.35, w: 5.4, colW: [1.6, 2.4, 1.4], fontSize: 17, rowH: 0.55, border: { type: "solid", pt: 0.75, color: "E0E0E0" }, valign: "middle" });
  txt(s, "Same bank, 10 days with no update: 8 + 25 + 25 = 58 → Medium", { x: 7.05, y: 5.4, w: 5.4, h: 0.9, fontSize: 16, italic: true, color: C.accent3 });
  s.addNotes("[Radhey] Data quality is the most important part of a medical tool. The scraper has a circuit breaker: if more than 20 percent of requests fail, it stops. dbt runs 37 data tests: no missing keys, no duplicate banks, and only valid blood groups. The anomaly gate blocks publishing if the bank count drops below 80 percent. And every bank gets a trust score out of 100. In this example, a bank updated two days ago gets 35 for freshness, 25 for a valid phone, and 25 for reporting four components: 85, which is High. If it stops updating for ten days, it drops to 58, Medium.");

  // ---------- 10. Testing ----------
  pres.addSection({ title: "Results" });
  s = content("Results", "Tested at every layer, on desktop and mobile");
  const stats = [["98", "pytest unit and API tests"], ["37", "dbt data tests"], ["146", "Playwright browser checks"], ["7", "screen widths, phone to desktop"]];
  stats.forEach(([n, l], i) => {
    const x = 0.6 + i * 3.08;
    card(s, x, 1.6, 2.85, 2.5, "stat card " + (i + 1));
    txt(s, n, { x, y: 1.8, w: 2.85, h: 1.15, fontSize: 60, bold: true, color: C.accent1, align: "center", fontFace: THEME.headFontFace });
    txt(s, l, { x: x + 0.2, y: 3.05, w: 2.45, h: 0.8, fontSize: 17, align: "center", color: C.accent3 });
  });
  const res = ["All tests pass; zero console errors on desktop and mobile", "28 documented test cases with expected and actual results", "CSV exports open correctly in Excel, Google Sheets and pandas", "Offline mode verified: app shell loads with no internet"];
  res.forEach((t, i) => {
    const y = 4.5 + i * 0.55;
    s.addImage({ data: iconRed.ok, x: 0.6, y: y + 0.06, w: 0.32, h: 0.32, objectName: "result icon " + (i + 1) });
    txt(s, t, { x: 1.1, y, w: 11.5, h: 0.45, fontSize: 18 });
  });
  s.addNotes("[Radhey] We tested every layer. 98 pytest tests cover the scraper, scoring, compatibility rules, CSV export and every API endpoint. 37 dbt tests check the data itself. Our Playwright script clicks through the real website like a user: 146 checks on desktop and mobile, failing on any console error. We also checked the layout at seven screen widths, from 360 to 1920 pixels. We documented 28 test cases in the report, verified CSV files in Excel, Google Sheets and pandas, and confirmed the app loads offline.");

  // ---------- 11. Limitations & future ----------
  s = content("Results", "Honest limits today, and a clear path forward");
  const cols = [
    ["Limitations", iconRed.limit, ["Snapshot every 6 hours, not live: call first", "Depends on banks updating eRaktKosh", "Map shows district centres, not exact address", "'Near me' needs HTTPS; English only"]],
    ["Future scope", iconRed.plus, ["SMS / WhatsApp alerts for rare groups", "Donor registration and blood-drive matching", "Hospital login for direct stock updates", "Demand forecasting and regional languages"]],
  ];
  cols.forEach(([h, ic, items], i) => {
    const x = 0.6 + i * 6.2;
    card(s, x, 1.55, 5.93, 4.3, h + " card");
    s.addImage({ data: ic, x: x + 0.3, y: 1.8, w: 0.5, h: 0.5, objectName: h + " icon" });
    txt(s, h, { x: x + 0.95, y: 1.78, w: 4.5, h: 0.55, fontSize: 24, bold: true, color: C.accent1, valign: "middle" });
    txt(s, items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } })),
      { x: x + 0.35, y: 2.6, w: 5.3, h: 3.7, fontSize: 19, paraSpaceAfter: 14 });
  });
  s.addNotes("[Shruti] We want to be honest about the limits. The data is a snapshot every six hours, not live, so users should always call before travelling. Accuracy depends on banks updating eRaktKosh. The map shows district centres, not exact hospital addresses. 'Near me' needs HTTPS, and the interface is English only. For the future: SMS or WhatsApp alerts when a rare group becomes available, donor registration, a hospital login so banks can update stock directly, demand forecasting once we have enough history, and regional languages.");

  // ---------- 12. Conclusion ----------
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Results" });
  txt(s, "Raktsetu turns scattered public data into a life-saving search", { x: 0.8, y: 0.6, w: 11.7, h: 1.2, fontSize: 32, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: "middle" });
  const take = [["Impact", "4,716 banks searchable in seconds, with compatible groups"], ["Learning", "Real data engineering: lakehouse, dbt, testing, PWA"], ["Working product", "Tested, documented and ready to deploy"]];
  take.forEach(([h, d], i) => {
    const x = 0.8 + i * 3.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.2, w: 3.65, h: 2.2, rectRadius: 0.12, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "takeaway " + (i + 1) });
    txt(s, h, { x: x + 0.3, y: 2.45, w: 3.05, h: 0.5, fontSize: 22, bold: true, color: C.background1 });
    txt(s, d, { x: x + 0.3, y: 3.05, w: 3.05, h: 1.2, fontSize: 18, color: C.background1 });
  });
  txt(s, "Questions?", { x: 0.8, y: 4.85, w: 6, h: 0.9, fontSize: 40, bold: true, color: C.background1, fontFace: THEME.headFontFace });
  txt(s, "Thank you  ·  Demo / GitHub: [add link here]", { x: 0.8, y: 5.8, w: 11.7, h: 0.5, fontSize: 18, color: C.accent2 });
  s.addNotes("[Shruti] To conclude: Raktsetu turns scattered public data into a search that can save lives. 4,716 blood banks are now searchable in seconds, with compatible groups and a trust score. For us, it was real data engineering: a lakehouse, dbt, automated testing and a progressive web app. And it is a working product: tested, documented and ready to deploy. Thank you. We are happy to take your questions.");

  // ---------- Backup (hidden) ----------
  pres.addSection({ title: "Backup" });
  const backupImg = (title, file, w, h, note) => {
    const b = content("Backup", title);
    b.hidden = !process.env.SHOW;
    b.addImage({ path: ROOT + file, x: (W - w) / 2, y: 1.4, w, h, objectName: title });
    b.addNotes(note);
  };
  backupImg("Backup: ER diagram of the gold tables", "docs/diagrams/er_diagram.png", 4.1, 5.5, "Backup. hospital_code links every gold table to dim_blood_banks.");
  backupImg("Backup: DFD Level 1", "docs/diagrams/dfd_level1.png", 3.42, 5.5, "Backup. Six processes and four data stores.");
  backupImg("Backup: Emergency search sequence", "docs/diagrams/sequence_diagram.png", 4.97, 5.5, "Backup. Browser → FastAPI → medical rules → DuckDB → ranked JSON.");
  backupImg("Backup: Detailed architecture", "docs/diagrams/architecture_diagram.png", 3.31, 5.5, "Backup. Full architecture diagram from the report.");

  s = content("Backup", "Backup: Main API endpoints");
  s.hidden = !process.env.SHOW;
  const api = [["Endpoint", "Used for"], ["GET /api/search", "Blood Finder and map"], ["GET /api/v1/emergency", "Emergency Mode ranking"], ["GET /api/v1/shortages", "District shortages"], ["GET /api/v1/rare", "Rare Blood Radar"], ["GET /api/history", "Trend chart"], ["GET /api/v1/health/dashboard", "Data Health panel"], ["GET /api/v1/export/*.csv", "CSV downloads"]]
    .map((r, i) => r.map((c) => ({ text: c, options: { bold: i === 0, color: i === 0 ? C.background1 : C.text1, fill: { color: i === 0 ? C.accent1 : C.background1 } } })));
  s.addTable(api, { x: 1.5, y: 1.5, w: 10.3, colW: [5.3, 5.0], fontSize: 18, rowH: 0.6, border: { type: "solid", pt: 0.75, color: "E0E0E0" }, valign: "middle" });
  s.addNotes("Backup. Full list with parameters at /docs (Swagger UI).");

  s = content("Backup", "Backup: Likely viva questions");
  s.hidden = !process.env.SHOW;
  const qa = [
    ["Why DuckDB, not MySQL?", "Analytics workload, no server, reads Parquet."],
    ["Is the data real?", "Yes, eRaktKosh (MoHFW); no fake data."],
    ["What if eRaktKosh is down?", "Circuit breaker + gate; old data stays live."],
    ["How is Emergency rank made?", "0.35 fresh + 0.30 trust + 0.25 units + 0.10 distance."],
    ["Why is plasma different?", "Reverse rule: AB is the universal plasma donor."],
    ["How do you stop SQL injection?", "All values passed as ? parameters."],
  ];
  qa.forEach(([q, a], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 6.2, y = 1.5 + row * 1.7;
    card(s, x, y, 5.93, 1.45, "qa card " + (i + 1));
    txt(s, q, { x: x + 0.3, y: y + 0.18, w: 5.4, h: 0.45, fontSize: 19, bold: true, color: C.accent1 });
    txt(s, a, { x: x + 0.3, y: y + 0.7, w: 5.4, h: 0.55, fontSize: 17 });
  });
  s.addNotes("Backup. More answers in docs/guide/16_GLOSSARY_AND_FAQ.md.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("saved", OUT);
})();
