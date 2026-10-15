# BloodGrid Legal, Compliance & Attribution Architecture

> [!WARNING]
> **LEGAL NOTICE & DISCLAIMER**:  
> The policies and assessments contained within this document are technical drafts prepared for system compliance and operational readiness. They do not constitute formal legal advice. Prior to commercial operation, all draft documents must be reviewed and countersigned by an advocate qualified in the jurisdiction of the Republic of India.

---

## 1. Data Source Attribution & Intellectual Property

### 1.1 Source Attribution Statement
BloodGrid ingests publicly accessible blood stock metrics published by:
- **Source**: eRaktKosh Portal (`eraktkosh.mohfw.gov.in`)
- **Authority**: Ministry of Health & Family Welfare (MoHFW), Government of India
- **Implementing Agencies**: National Health Mission (NHM) & Centre for Development of Advanced Computing (C-DAC)

Every page, API response, alert dispatch, and exported report in BloodGrid carries the mandatory attribution notice:
```text
Data sourced from eRaktKosh (Ministry of Health & Family Welfare, Govt. of India). 
Not an official service. Always call the blood bank to confirm before travelling.
```

### 1.2 Non-Affiliation Guarantee
BloodGrid is an independent open-access health analytics platform. BloodGrid **never** represents itself as an official government agency, department, or designated representative of MoHFW, NHM, or CDAC.

---

## 2. Terms of Use Review & Permitted / Prohibited Actions

### 2.1 What BloodGrid Does (Permitted)
1. **Value-Added Processing**: BloodGrid transforms disjointed, semi-structured district-level metrics into structured time-series snapshots, spatial availability indexes, and automated emergency alert notifications.
2. **Polite Harvesting**: Automated queries implement strict concurrency throttles (10 workers), exponential backoff with jitter on HTTP 429/5xx, a minimum 3-hour interval guard between runs, an automated circuit breaker tripping at >20% failure, and explicit contact information in the HTTP `User-Agent`.
3. **Emergency Transparency**: Aggregates emergency contact numbers and blood bank operational statuses for non-commercial public utility and NGO coordination.

### 2.2 What BloodGrid Prohibits (Strictly Prohibited)
1. **No Resale of Raw Data**: BloodGrid strictly prohibits and forbids selling raw eRaktKosh datasets or charging fees merely to view raw government figures. Commercial pricing applies solely to computational infrastructure: custom alerting webhooks, programmatic API rate limits, time-series aggregations, and automated shortage forecasting.
2. **No Deceptive Branding**: No use of the State Emblem of India, MoHFW crest, or misleading visual cues that imply governmental backing.
3. **No Storage of Donor Medical Records**: BloodGrid never collects, requests, stores, or processes individual donor blood test results, screening records, or transfusion clinical histories.
4. **No Resale of Blood**: Under the Drugs and Cosmetics Act, 1940 and Supreme Court directives (*Common Cause v. Union of India*, 1996), commercial trading or profiting from blood and blood products is illegal in India. BloodGrid has zero involvement in the physical handling, pricing, or transaction of blood units.

---

## 3. Formal Government Outreach: Draft NIC / NHM Email

To establish official coordination and request authorized API access or a formal Memorandum of Understanding (MoU), use the following draft:

```text
To: eraktkosh@cdac.in, contact-eraktkosh@gov.in, nhm-india@nic.in
Subject: BloodGrid: Public Transparency & Notification Infrastructure for eRaktKosh

Respected Officers,

I am writing on behalf of the BloodGrid engineering initiative (https://bloodgrid.in), an independent, public-interest blood availability platform developed from Anand, Gujarat.

BloodGrid indexes district blood bank component availability metrics published on the eRaktKosh portal to provide citizens, NGOs, and emergency trauma responders with:
1. Real-time emergency stock verification with contact numbers.
2. Automated shortage notifications for voluntary donor organizations when critical negative or Bombay blood groups are depleted.
3. Predictive blood camp planning recommendations to address regional stock deficits.

We maintain strict ethical engineering safeguards:
- Concurrency throttles (<=10 requests) and respectful intervals (>3 hours between crawls) to ensure zero impact on portal server load.
- Mandatory attribution on every page and API response stating data originates from eRaktKosh (MoHFW) and that BloodGrid is an independent service.
- Transparent contact header: BloodGrid-DataCollector/1.0 (+https://bloodgrid.in; data@bloodgrid.in).

We would welcome the opportunity to:
a) Transition to an authorized direct API endpoint or data exchange feed if available.
b) Formally align our shortage radar with NHM/National Blood Transfusion Council (NBTC) guidelines via an MoU or academic/civil society collaboration.

Please advise on the appropriate office or department with whom we may review our technical architecture.

Warm regards,

Radhey Gajera
Lead Engineer, BloodGrid
Contact: +91 98765 43210 | data@bloodgrid.in | Anand, Gujarat
```

---

## 4. Digital Personal Data Protection (DPDP) Act 2023 Compliance

BloodGrid complies with the principles of the **Digital Personal Data Protection Act, 2023**:

| DPDP Principle | BloodGrid Implementation |
| :--- | :--- |
| **Purpose Limitation** | Contact details (email or Telegram handle) are collected solely to deliver user-configured blood shortage alerts. They are never sold, rented, or repurposed for marketing. |
| **Data Minimization** | We collect only: email address or Telegram ID, target district, and blood group of interest. No names, national IDs (Aadhaar/PAN), or home addresses are collected for alerts. |
| **Notice & Consent** | Alert creation requires an explicit affirmative checkbox agreeing to emergency notification delivery. |
| **Right to Erasure** | Users can unsubscribe in one click via a signed token in every alert email, or delete their profile from the user dashboard (`/dashboard`), triggering an immediate cascade delete. |
| **Security Safeguards** | API tokens and user passwords are encrypted using Argon2id and SHA-256 digests. Sensitive subscriber details are segregated from analytical databases. |
| **Minimal Retention** | Inactive alert subscriptions without user confirmation after 90 days are automatically pruned. |

---

## 5. Commercial Policies (Drafts for Counsel Review)

### 5.1 Draft Terms of Service
- **Scope**: Governing access to the BloodGrid platform, web interface, and REST API.
- **Accuracy Disclaimer**: Blood availability numbers reflect periodic voluntary updates submitted by blood centers to eRaktKosh. Real-time bed-side emergencies require direct telephone confirmation prior to dispatch.
- **Fair Use**: API rate limits are enforced automatically based on tier. Scraping the BloodGrid API without authorization or bypassing rate limits results in immediate IP/key revocation.

### 5.2 Draft Privacy Policy
- **Data Controller**: BloodGrid India Operations, Anand, Gujarat.
- **Personal Data Collected**: Email address, encrypted password hash, optional organization name, and alert subscription criteria.
- **Data Subject Rights**: Right to access, right to rectification, right to erasure, and right to grievance redressal via `privacy@bloodgrid.in`.

### 5.3 Draft Refund Policy
- **Billing**: Recurring subscriptions for Developer and Organization tiers are billed monthly via Razorpay.
- **Cancellations**: Subscriptions can be cancelled at any time from the account console. Cancellation takes effect at the end of the current billing cycle.
- **Refund Window**: 7-day no-questions-asked refund for first-time annual subscriptions if API uptime falls below 99.5%.

### 5.4 Draft Medical Disclaimer
- **Emergency Protocol**: BloodGrid is an informational directory and notification utility. It is **not** a healthcare provider, clinical blood bank, or dispatch service. In any medical emergency, users must contact emergency medical services (108/112) or the attending hospital physician immediately.
