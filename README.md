# Version Monitor Agent

Monitors **Apache Tomcat** and **PostgreSQL** releases for DSR (JDK8 and JDK21), sends an HTML email when versions change, and updates the version JSON files in GitHub.

## What it does

1. Fetches latest Tomcat and PostgreSQL versions from vendor sites
2. Compares them with `versions_jdk8.json` and `versions_jdk21.json`
3. If something changed → sends email and saves updated JSON
4. Jenkins commits and pushes JSON changes to `main`

## Components monitored

| JDK   | Apache Tomcat | PostgreSQL |
|-------|---------------|------------|
| JDK8  | Tomcat 9.0.x  | Latest release |
| JDK21 | Tomcat 11.0.x | Latest release |

## Local run

```bash
pip install -r requirements.txt
```

Create a `.env` file (not committed):

```env
EMAIL_USER=your-sender@gmail.com
EMAIL_PASS=your-gmail-app-password
EMAIL_RECIPIENTS=email1@example.com,email2@example.com
```

```bash
python agent.py
```

## Project files

| File | Purpose |
|------|---------|
| `agent.py` | Fetches versions, compares, emails, updates JSON |
| `email_template.py` | HTML email layout |
| `versions_jdk8.json` | JDK8 component versions |
| `versions_jdk21.json` | JDK21 component versions |
| `requirements.txt` | Python dependencies |
