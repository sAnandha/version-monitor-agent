# Version Monitor Agent — Project Explanation

## 1. Overview

The **Version Monitor Agent** is an automated monitoring system built for the **DSR (Document Security & Rights)** platform team at ASSA ABLOY. Its purpose is to:

1. **Scrape** the latest released versions of **Apache Tomcat** and **PostgreSQL** from official vendor websites.
2. **Compare** those versions against locally stored baseline data for two JDK environments (JDK8 and JDK21).
3. **Notify** the team via email when a newer version is detected.
4. **Persist** updated version numbers back to the repository so the next run compares against the latest known state.

The project runs entirely in the cloud using **GitHub Actions** — there is no dedicated server, VM, or traditional OS-level cron job. Scheduling is handled by GitHub's built-in workflow scheduler.

**Repository:** [https://github.com/sAnandha/version-monitor-agent](https://github.com/sAnandha/version-monitor-agent)

---

## 2. How the Project Was Created

The project was built incrementally over **June 25–29, 2026**, through a series of commits on the `main` branch. Below is the evolution timeline.

### Phase 1 — Initial Scaffold (June 25, 2026)

The first commits established the core skeleton:

| Commit | File | What was added |
|--------|------|----------------|
| `6c934eb` | `agent.py` | Main Python script using `requests` + `BeautifulSoup` to scrape Tomcat 9, Tomcat 11, and PostgreSQL versions |
| `0235d06` | `requirements.txt` | Python dependencies: `requests`, `beautifulsoup4` |
| `c984375` | `versions.json` | Single JSON file holding version state for all components |
| `e4b6b81` | `.github/workflows/monitor.yml` | GitHub Actions workflow with cron schedule (`0 3 * * *` UTC) and manual trigger |

The original design used one shared `versions.json` file and BeautifulSoup for HTML parsing.

### Phase 2 — Split by JDK & Email Config (June 25, 2026)

| Change | Purpose |
|--------|---------|
| Created `versions_jdk8.json` and `versions_jdk21.json` | Separated version tracking for JDK8 (Tomcat 9) and JDK21 (Tomcat 11) DSR releases |
| Deleted `versions.json` | Replaced single file with JDK-specific files |
| Created `emails.json` | Centralized email recipient list |
| Updated `agent.py` | Adapted logic to read/write two JSON files and load recipients from `emails.json` |
| Added GitHub Secrets (`EMAIL_USER`, `EMAIL_PASS`) | Gmail SMTP credentials injected at runtime |

### Phase 3 — Auto-Commit & Permissions (June 25–26, 2026)

The workflow was enhanced so that after the agent runs, updated JSON files are automatically committed and pushed back to `main`:

- Added `permissions: contents: write` to the workflow
- Added a **Commit Updated JSON Files** step that runs `git add`, `git commit`, and `git push`
- This creates audit trail commits like `"Auto update version JSON"`

### Phase 4 — Email Template Module (June 28, 2026)

| Change | Purpose |
|--------|---------|
| Created `email_template.py` | Separated HTML email generation from scraping logic |
| Refactored `agent.py` | Switched from BeautifulSoup to regex-based parsing; imports `build_email` from `email_template` |
| Updated JSON structure | Added rich metadata: DSR version columns, release dates, comments, current component versions |

### Phase 5 — Schedule Tuning & Stabilization (June 26–29, 2026)

- Cron schedule adjusted from `0 3 * * *` (3:00 AM UTC) to **`30 5 * * *`** (5:30 AM UTC = **11:00 AM IST**)
- Python upgraded from 3.10 → **3.11**
- GitHub Actions checkout upgraded to `@v4`, setup-python to `@v5`
- Manual data updates to JSON files (DSR version mappings, comments, release dates)
- Email recipient list refined via PR #1

---

## 3. Project Structure

```
version-monitor-agent/
├── agent.py                  # Main entry point — scraping, comparison, email dispatch
├── email_template.py         # HTML email builder with styled tables
├── emails.json               # Email recipient list
├── versions_jdk8.json        # Version state for JDK8 / Tomcat 9 environment
├── versions_jdk21.json       # Version state for JDK21 / Tomcat 11 environment
├── requirements.txt          # Python dependencies
├── README.md                 # Minimal readme (trigger schedule note)
├── Explanation.md            # This document
└── .github/
    └── workflows/
        └── monitor.yml       # GitHub Actions CI/CD workflow (cron + manual)
```

---

## 4. Tools & Technologies Used

| Tool / Technology | Role in the Project |
|-------------------|---------------------|
| **Python 3.11** | Core runtime language |
| **requests** | HTTP client to fetch vendor web pages (Tomcat, PostgreSQL) |
| **beautifulsoup4** | Listed in `requirements.txt`; used in early versions for HTML parsing. Current `agent.py` uses **regex** instead, but the dependency is still installed in CI |
| **smtplib** (stdlib) | Sends email via Gmail SMTP (`smtp.gmail.com:587` with STARTTLS) |
| **email.mime** (stdlib) | Constructs multipart HTML email messages |
| **json** (stdlib) | Reads/writes version state and recipient configuration |
| **re** (stdlib) | Regex extraction of version numbers from HTML page text |
| **copy.deepcopy** (stdlib) | Preserves original JSON snapshots before mutation |
| **GitHub Actions** | Cloud CI runner — replaces traditional cron + server |
| **GitHub Secrets** | Stores `EMAIL_USER` and `EMAIL_PASS` securely |
| **Gmail SMTP** | Outbound email delivery channel |

---

## 5. Data Files Explained

### 5.1 `versions_jdk8.json`

Tracks components for the **JDK8** DSR release line:

- **Apache Tomcat 9** — latest stable from [Tomcat 9 download page](https://tomcat.apache.org/download-90.cgi)
- **PostgreSQL** — latest from [PostgreSQL release notes](https://www.postgresql.org/docs/release/)

Each component stores:
- `dsrVersions` — which Tomcat/Postgres version shipped in each DSR release (e.g., DSR 8.0.42, DSR 9.0.25)
- `latestComponentVersion` — last known latest version from vendor (updated by the agent)
- `releaseDate`, `currentComponentVersion`, `comments` — manually maintained team notes

### 5.2 `versions_jdk21.json`

Same structure for the **JDK21** line, but:
- Uses **Tomcat 11** instead of Tomcat 9
- References future DSR releases (DSR 8.0.100, DSR 9.0.100)
- Omits `currentComponentVersion` column in the email table

### 5.3 `emails.json`

```json
{
  "recipients": [
    "updatesmailtrigger@gmail.com",
    "tejabontha@gmail.com",
    "anandhanivas.saravanadurai@assaabloy.com"
  ]
}
```

Recipients are loaded at send time. This file is **not** auto-updated by the agent.

---

## 6. How Everything Calls Each Other

### 6.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Scheduler                      │
│              cron: "30 5 * * *"  OR  workflow_dispatch           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  .github/workflows/monitor.yml                   │
│  1. Checkout repo                                                │
│  2. Setup Python 3.11                                            │
│  3. pip install requests beautifulsoup4                          │
│  4. python agent.py  (with EMAIL_USER, EMAIL_PASS secrets)       │
│  5. git commit + push updated JSON files                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         agent.py                                 │
│                                                                  │
│  process()                                                       │
│    ├── load_json("versions_jdk8.json")                          │
│    ├── load_json("versions_jdk21.json")                         │
│    ├── get_tomcat9()  ──→ requests.get → regex → "9.0.xxx"      │
│    ├── get_tomcat11() ──→ requests.get → regex → "11.x.xx"      │
│    ├── get_postgres() ──→ requests.get → regex → "xx.x"         │
│    ├── update_component() for each matching component            │
│    │     └── compares latestComponentVersion vs scraped version  │
│    ├── IF changed:                                               │
│    │     ├── build_email(jdk8, jdk21)  ──→ email_template.py    │
│    │     ├── send_email(html)                                      │
│    │     │     ├── load_recipients() ──→ emails.json             │
│    │     │     └── smtplib → Gmail SMTP                           │
│    │     └── save_json() for both JDK files                        │
│    └── ELSE: print "No version changes detected."                │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Detailed Call Chain

#### Step 1 — Workflow triggers `agent.py`

```yaml
run: python agent.py
```

When executed, the `if __name__ == "__main__"` block calls `process()`.

#### Step 2 — `process()` loads state

```python
jdk8 = load_json(JDK8_FILE)    # versions_jdk8.json
jdk21 = load_json(JDK21_FILE)  # versions_jdk21.json
```

Deep copies are kept (`original8`, `original21`) though they are not currently used for diffing — the change detection happens inline during updates.

#### Step 3 — Version scraping

Three independent HTTP fetch functions run sequentially:

| Function | URL | Regex Pattern | Example Result |
|----------|-----|---------------|----------------|
| `get_tomcat9()` | `tomcat.apache.org/download-90.cgi` | `\b9\.0\.\d+\b` | `9.0.119` |
| `get_tomcat11()` | `tomcat.apache.org/tomcat-11.0-doc/index.html` | `\b11\.\d+\.\d+\b` | `11.0.23` |
| `get_postgres()` | `postgresql.org/docs/release/` | `PostgreSQL\s+(\d+\.\d+)` | `18.4` |

Each function:
1. Calls `requests.get(url, timeout=20)`
2. Calls `r.raise_for_status()` to fail on HTTP errors
3. Searches `r.text` with `re.search()`
4. Returns matched version string or `"Unknown"`

#### Step 4 — Component update loop

For **JDK8** components:
- `"Apache Tomcat"` → compared against scraped Tomcat 9 version
- `"PostgreSQL"` → compared against scraped PostgreSQL version

For **JDK21** components:
- `"Apache Tomcat"` → compared against scraped Tomcat 11 version
- `"PostgreSQL"` → compared against scraped PostgreSQL version

`update_component(component, latest_version)` sets `component["latestComponentVersion"]` if different and returns `True`/`False`.

#### Step 5 — Email generation (only if something changed)

```python
html = build_email(jdk8, jdk21)   # email_template.py
send_email(html)
```

**`email_template.py` call chain:**

```
build_email(jdk8_data, jdk21_data)
  ├── build_table(jdk8_data, show_current=True)   → JDK8 HTML table
  ├── build_table(jdk21_data, show_current=False)  → JDK21 HTML table
  └── wraps both in HTML email with TABLE_STYLE CSS
```

Each `build_table()` reads:
- `data["title"]` — section heading (e.g., "JDK8")
- `data["headers"]` — column header labels
- `data["components"]` — row data with icons (🧩 Tomcat, 🐘 PostgreSQL)

#### Step 6 — Email sending

```python
send_email(html)
  ├── load_recipients() → emails.json → ["email1@...", ...]
  ├── MIMEMultipart("alternative") with HTML body
  └── smtplib.SMTP("smtp.gmail.com", 587)
        ├── starttls()
        ├── login(EMAIL_USER, EMAIL_PASS)
        └── sendmail(EMAIL_USER, recipients, msg)
```

Environment variables `EMAIL_USER` and `EMAIL_PASS` are injected by GitHub Actions from repository secrets.

#### Step 7 — Persist updated JSON

```python
save_json(JDK8_FILE, jdk8)
save_json(JDK21_FILE, jdk21)
```

Only runs if at least one component version changed.

#### Step 8 — Workflow auto-commits

After `agent.py` finishes, the workflow step:

```bash
git add versions_jdk8.json versions_jdk21.json
git commit -m "Auto update version JSON" || echo "No changes to commit"
git push origin main
```

This ensures the repository always reflects the last notified version, preventing duplicate emails on the next run.

---

## 7. How Cron Is Performed

This project does **not** use a traditional Linux cron daemon (`crontab -e`). Instead, scheduling is handled entirely by **GitHub Actions**.

### 7.1 Schedule Configuration

In `.github/workflows/monitor.yml`:

```yaml
on:
  schedule:
    # Runs every day at 11:00 AM IST (05:30 UTC)
    - cron: "30 5 * * *"

  workflow_dispatch:
```

### 7.2 Cron Syntax Breakdown

```
"30 5 * * *"
  │  │ │ │ │
  │  │ │ │ └── Day of week (0–7, * = every day)
  │  │ │ └──── Month (1–12, * = every month)
  │  │ └────── Day of month (1–31, * = every day)
  │  └──────── Hour (0–23, UTC) → 5 = 5 AM UTC
  └─────────── Minute → 30

Result: Every day at 05:30 UTC = 11:00 AM IST (UTC+5:30)
```

### 7.3 How GitHub Actions Cron Works

1. GitHub's infrastructure maintains a global job queue for scheduled workflows.
2. At the configured UTC time, GitHub enqueues a workflow run for this repository.
3. A fresh **Ubuntu latest** virtual machine is provisioned.
4. The workflow steps execute sequentially (checkout → setup Python → install deps → run agent → commit).
5. The VM is destroyed after the job completes.

**Important notes about GitHub Actions scheduling:**

- Schedules only run on the **default branch** (`main`).
- During high GitHub load, scheduled runs may be delayed by a few minutes.
- If the repository has no activity for 60 days, scheduled workflows may be disabled automatically.
- The minimum interval is once every 5 minutes (this project runs once daily).

### 7.4 Email Behavior on Scheduled Runs

The cron schedule only controls **when** the agent runs — it does **not** send an email on every run.

| Scenario | Workflow runs? | Email sent? | JSON committed? |
|----------|----------------|-------------|-----------------|
| Cron fires, **no version change** | Yes | **No** | No |
| Cron fires, **version changed** | Yes | **Yes** | Yes |
| Manual trigger, no change | Yes | **No** | No |
| Manual trigger, version changed | Yes | **Yes** | Yes |

**This is the most common reason people think the schedule "doesn't work":** the workflow runs successfully at 11:00 AM IST, prints `No version changes detected.`, sends no email, and creates no commit — which looks like nothing happened unless you open the **Actions** tab.

```
Cron / manual trigger
        ↓
GitHub Actions runs agent.py
        ↓
Scrape & compare versions
        ↓
   ┌────┴────┐
   │         │
NO CHANGE   CHANGE
   │         │
   ↓         ↓
No email    Email sent
No commit   JSON committed
```

### 7.5 Manual Trigger (`workflow_dispatch`)

The workflow can also be triggered manually from the GitHub UI:

**Actions → Version Monitor Agent → Run workflow**

This is useful for testing without waiting for the daily schedule.

### 7.6 Cron Schedule History

| Date | Cron Expression | Meaning |
|------|-----------------|---------|
| Initial (Jun 25) | `0 3 * * *` | 3:00 AM UTC (8:30 AM IST) |
| Current | `30 5 * * *` | 5:30 AM UTC (11:00 AM IST) |

### 7.7 Production Deployment on GitHub

When hosted on GitHub, the project runs entirely through **GitHub Actions** — no server or VM is required.

**Setup checklist:**

1. Push all code to the **`main`** branch (schedule only works from the default branch).
2. Enable Actions: **Settings → Actions → General → Allow all actions**.
3. Add secrets: **Settings → Secrets and variables → Actions**
   - `EMAIL_USER` — sender Gmail address
   - `EMAIL_PASS` — Gmail App Password (16 chars, no spaces)
4. Confirm workflow file exists at `.github/workflows/monitor.yml` on `main`.
5. Wait for the next scheduled time (**11:00 AM IST daily**) or use **Run workflow** to test immediately.

**How automatic trigger works in production:**

```
Every day at 05:30 UTC (11:00 AM IST)
        │
        ▼
GitHub scheduler enqueues "Version Monitor Agent" workflow
        │
        ▼
Ubuntu runner starts → checkout → Python → agent.py
        │
        ├── No version change → workflow succeeds silently (no email, no commit)
        │
        └── Version changed → email sent → JSON committed → pushed to main
```

**How to verify a scheduled run actually happened:**

1. Open **Actions** tab on GitHub.
2. Look for a run with event **`schedule`** (not `workflow_dispatch`).
3. Open the run log → step **"Log trigger source"** shows `Event name: schedule`.
4. Step **"Run Version Monitor Agent"** shows either:
   - `No version changes detected.` (normal — schedule worked, nothing to report)
   - `Email sent and JSON updated.` (change detected)

### 7.8 Why Schedule May Appear Broken (Troubleshooting)

| Symptom | Likely cause | What to check |
|---------|--------------|---------------|
| Manual works, schedule "does nothing" | No version change on scheduled run | Actions tab — look for green `schedule` runs |
| No email after schedule | Expected when versions unchanged | Lower `latestComponentVersion` in JSON to test |
| Schedule never appears in Actions | Workflow not on `main` branch | Merge workflow to default branch |
| Yellow banner in Actions | Scheduled workflows disabled (60-day inactivity) | Click **Enable workflow** in Actions tab |
| Fork repo | Scheduled workflows disabled by default on forks | **Settings → Actions → General → Enable workflows** |
| Expected run at wrong time | Cron is **UTC**, not IST | `30 5 * * *` = 11:00 AM IST, not 5:30 AM IST |
| Deployed today, no run yet | Schedule fires once per day at fixed UTC time | Wait until next 11:00 AM IST window |
| Run delayed 30–90 minutes | GitHub queue load at peak hours | Normal — check Actions tab later |

**Evidence from this repository:** Git commits authored by `github-actions` (e.g. `"Auto update version JSON"`) prove scheduled runs have executed successfully in the past. Runs at times like 14:50–15:05 UTC were likely **manual** `workflow_dispatch` triggers during development, not the daily 05:30 UTC cron.

---

## 8. Environment Variables & Secrets

| Variable | Source | Purpose |
|----------|--------|---------|
| `EMAIL_USER` | GitHub Secret | Gmail account address used as SMTP sender |
| `EMAIL_PASS` | GitHub Secret | Gmail App Password (not regular account password) |

These are **never** stored in the repository. They are configured under:

**GitHub Repository → Settings → Secrets and variables → Actions**

---

## 9. Email Output Example

When a version change is detected, recipients receive an HTML email with:

- **Subject:** `Version Update Summary – Postgres and Apache Tomcat`
- **Body:** Two styled HTML tables:
  - **JDK8 table** — includes Component Name, DSR version columns, Latest Version, Release Date, Current Version, Comments
  - **JDK21 table** — same but without Current Version column
- **Footer:** "Thanks & Regards, Version Monitor Agent"

If no version changes are detected, **no email is sent** and the JSON files are not updated.

---

## 10. End-to-End Execution Sequence

```
Daily at 11:00 AM IST
        │
        ▼
GitHub Actions starts "Version Monitor Agent" workflow
        │
        ▼
Checkout code from main branch
        │
        ▼
Install Python 3.11 + requests + beautifulsoup4
        │
        ▼
Run: python agent.py
        │
        ├── Fetch Tomcat 9, Tomcat 11, PostgreSQL versions from web
        ├── Load versions_jdk8.json + versions_jdk21.json
        ├── Compare scraped versions vs stored latestComponentVersion
        │
        ├── [NO CHANGE] → Print message → Workflow ends (no commit)
        │
        └── [CHANGE DETECTED]
              ├── Build HTML email via email_template.py
              ├── Send email to recipients in emails.json via Gmail SMTP
              ├── Save updated JSON files locally on runner
              └── Workflow commits + pushes JSON to main
                        │
                        ▼
              Team receives email notification
              Repository updated with new baseline versions
```

---

## 11. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| GitHub Actions instead of server cron | No infrastructure to maintain; free for public repos; built-in secret management |
| Separate JDK8/JDK21 JSON files | Different Tomcat major versions (9 vs 11) and different DSR release tracks |
| Email only on change | Avoids daily noise; team is notified only when action may be needed |
| Auto-commit JSON after email | Ensures next run compares against the last notified state |
| Regex over BeautifulSoup (current) | Simpler parsing for version strings embedded in page text |
| `email_template.py` as separate module | Clean separation of scraping logic vs presentation logic |
| Manual fields in JSON (comments, release dates, DSR mappings) | Automated scraping cannot know internal DSR release plans — team maintains context |

---

## 12. How to Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export EMAIL_USER="your@gmail.com"
export EMAIL_PASS="your-app-password"

# Run the agent
python agent.py
```

Locally, JSON files will update on change but nothing commits to Git — that only happens in CI.

---

## 13. Summary

The **Version Monitor Agent** is a lightweight, serverless automation that:

1. Runs on a **daily GitHub Actions cron schedule** (11:00 AM IST).
2. **Scrapes** Apache Tomcat and PostgreSQL vendor sites for latest versions.
3. **Compares** against persisted JSON state for JDK8 and JDK21 DSR environments.
4. **Emails** the team with a formatted HTML summary when versions change.
5. **Commits** updated JSON back to the repository to maintain state.

The entire system consists of two Python modules (`agent.py`, `email_template.py`), three JSON config/data files, and one GitHub Actions workflow — no databases, no containers, and no dedicated servers.
