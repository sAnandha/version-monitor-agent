""" 
This is the Python Based Agent allows to Compare 
the Latest Available version and Previous Version 
and Automatically Triggers mail if any Changes detected.

"""

import json
import os
import re
import smtplib
import requests

from dotenv import load_dotenv
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()
from email_template import build_email_jdk8, build_email_jdk21

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

JDK8_FILE = "versions_jdk8.json"
JDK21_FILE = "versions_jdk21.json"

RECIPIENTS_JDK8_ENV = "EMAIL_RECIPIENTS_JDK8"
RECIPIENTS_JDK21_ENV = "EMAIL_RECIPIENTS_JDK21"
CC_RECIPIENTS_JDK8_ENV = "EMAIL_CC_RECIPIENTS_JDK8"
CC_RECIPIENTS_JDK21_ENV = "EMAIL_CC_RECIPIENTS_JDK21"

URLS = {
    "Tomcat 9 Changelog": "https://tomcat.apache.org/tomcat-9.0-doc/changelog.html",
    "Tomcat 11 Changelog": "https://tomcat.apache.org/tomcat-11.0-doc/changelog.html",
    "PostgreSQL": "https://www.postgresql.org/docs/release/",
}

def get_tomcat9():
    r = requests.get(URLS["Tomcat 9 Changelog"], timeout=20)
    r.raise_for_status()
    version_match = re.search(r"Version\s+(9\.\d+\.\d+)", r.text)
    date_match = re.search(r'<time datetime="([^"]+)">', r.text)
    release_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")

    return {
        "version": version_match.group(1),
        "release_date": release_date,
    }

def get_tomcat11():
    r = requests.get(URLS["Tomcat 11 Changelog"], timeout=20)
    r.raise_for_status()
    version_match = re.search(r"Version\s+(11\.\d+\.\d+)", r.text)
    date_match = re.search(r'<time datetime="([^"]+)">', r.text)
    release_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")

    return {
        "version": version_match.group(1),
        "release_date": release_date,
    }

def parse_postgres_versions(html_text):
    """Extract individual version strings from the PostgreSQL release banner."""
    m = re.search(r"[A-Za-z]+\s+\d{1,2},\s+\d{4}:\s*(?:<[^>]*>)*\s*PostgreSQL\s+(.+?)\s*Released!",
        html_text,re.I | re.S,)
    if not m:
        return []

    raw = re.sub(r"<[^>]+>", "", m.group(1))
    raw = raw.replace(" and ", ", ")
    return [p.strip() for p in raw.split(",") if p.strip()]

def postgres_version_key(version_str):
    """
    Comparable tuple where higher values mean newer releases.
    Ordering: 20.3 > 20.0 > 20 Beta 5 > 19.2 > 19 Beta 3
    """
    v = version_str.replace("PostgreSQL", "").strip()
    beta = re.match(r"^(\d+)\s+Beta\s+(\d+)$", v, re.I)
    if beta:
        return (int(beta.group(1)), 0, int(beta.group(2)))

    final = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", v)
    if final:
        return (int(final.group(1)), 1, int(final.group(2)), int(final.group(3) or 0))

    major_only = re.match(r"^(\d+)$", v)
    if major_only:
        return (int(major_only.group(1)), 1, 0, 0)

    return (0, 0, 0)

def format_postgres_version(version_str):
    v = version_str.replace("PostgreSQL", "").strip()
    return f"PostgreSQL {v}"

def is_beta_version(version_str):
    v = version_str.replace("PostgreSQL", "").strip()
    return bool(re.match(r"^\d+\s+Beta\s+\d+$", v, re.I))

def get_last_major_version(component):
    if component.get("lastMajorVersion"):
        return component["lastMajorVersion"]
    stored = component["latestComponentVersion"]
    if not is_beta_version(stored):
        return stored.replace("PostgreSQL", "").strip()
    return component.get("currentComponentVersion", "0.0")


def pick_postgres_candidate(all_versions, last_major_version):
    """Prefer major when both types exist and major exceeds lastMajorVersion."""
    finals = [v for v in all_versions if not is_beta_version(v)]
    betas = [v for v in all_versions if is_beta_version(v)]
    last_major_key = postgres_version_key(last_major_version)

    if finals and betas:
        highest_final = max(finals, key=postgres_version_key)
        highest_beta = max(betas, key=postgres_version_key)
        if postgres_version_key(highest_final) > last_major_key:
            return highest_final, "both_major"
        return highest_beta, "both_beta"

    if finals:
        return max(finals, key=postgres_version_key), "final_only"
    if betas:
        return max(betas, key=postgres_version_key), "beta_only"
    return None, None


def should_update_postgres(stored_version, candidate, kind, last_major_version):
    candidate_fmt = format_postgres_version(candidate)
    if stored_version == candidate_fmt:
        return False

    candidate_key = postgres_version_key(candidate)
    stored_key = postgres_version_key(stored_version) if stored_version else (0, 0, 0)
    last_major_key = postgres_version_key(last_major_version)

    if kind == "both_major":
        return True

    if kind == "final_only":
        if stored_version and is_beta_version(stored_version):
            return candidate_key > last_major_key
        return candidate_key > stored_key

    return candidate_key > stored_key


def fetch_postgres_banner():
    r = requests.get(URLS["PostgreSQL"], timeout=20)
    r.raise_for_status()
    date_match = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4}):\s*.*?PostgreSQL\s+.+?\s*Released!",r.text,re.I | re.S,)
    release_date = date_match.group(1).strip() if date_match else "Unknown"
    return r.text, release_date


def resolve_postgres_version(html_text, release_date, stored_version=None, last_major_version=None):
    """Pick version using major/beta rules and dynamic lastMajorVersion floor."""
    all_versions = parse_postgres_versions(html_text)
    if not all_versions:
        return {"version": stored_version or "Unknown", "release_date": release_date}

    last_major = last_major_version or stored_version or "0.0"
    candidate, kind = pick_postgres_candidate(all_versions, last_major)
    if not candidate:
        return {"version": stored_version or "Unknown", "release_date": release_date}

    candidate_fmt = format_postgres_version(candidate)
    if should_update_postgres(stored_version, candidate, kind, last_major):
        return {"version": candidate_fmt, "release_date": release_date}

    return {"version": stored_version, "release_date": release_date}

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_recipients(env_var):
    raw = os.getenv(env_var, "")
    return [e.strip() for e in raw.split(",") if e.strip()]

def send_email(html, to_list, cc_list, subject):
    if not to_list:
        print(f"No To recipients configured for: {subject}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg.attach(MIMEText(html, "html"))

    # SMTP must deliver to everyone listed in To and Cc headers
    all_recipients = list(dict.fromkeys(to_list + cc_list))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.sendmail(EMAIL_USER, all_recipients, msg.as_string())

    print(f"Email sent: {subject}")
    return True

def update_tomcat_component(component, version, release_date):
    changed = False

    if component["latestComponentVersion"] != version:
        component["latestComponentVersion"] = version
        changed = True

    if component.get("releaseDate") != release_date:
        component["releaseDate"] = release_date
        changed = True

    return changed

def update_postgres_component(component, version, release_date):
    changed = False

    if component["latestComponentVersion"] != version:
        component["latestComponentVersion"] = version
        changed = True

    if not is_beta_version(version):
        bare = version.replace("PostgreSQL", "").strip()
        if component.get("lastMajorVersion") != bare:
            component["lastMajorVersion"] = bare
            changed = True

    if component.get("releaseDate") != release_date:
        component["releaseDate"] = release_date
        changed = True

    return changed

def process():
    jdk8 = load_json(JDK8_FILE)
    jdk21 = load_json(JDK21_FILE)

    pg_html, pg_date = fetch_postgres_banner()

    latest = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
    }

    changed_jdk8 = False
    changed_jdk21 = False

    for c in jdk8["components"]:
        if c["componentName"] == "Apache Tomcat":
            changed_jdk8 |= update_tomcat_component(c, latest["Tomcat 9"]["version"], latest["Tomcat 9"]["release_date"])
        elif c["componentName"] == "PostgreSQL":
            postgres = resolve_postgres_version(pg_html,pg_date,c["latestComponentVersion"],get_last_major_version(c),)
            changed_jdk8 |= update_postgres_component(c, postgres["version"], postgres["release_date"])

    for c in jdk21["components"]:
        if c["componentName"] == "Apache Tomcat":
            changed_jdk21 |= update_tomcat_component(c, latest["Tomcat 11"]["version"], latest["Tomcat 11"]["release_date"])
        elif c["componentName"] == "PostgreSQL":
            postgres = resolve_postgres_version(pg_html,pg_date,c["latestComponentVersion"],get_last_major_version(c),)
            changed_jdk21 |= update_postgres_component(c, postgres["version"], postgres["release_date"])

    if not changed_jdk8 and not changed_jdk21:
        print("No version changes detected.")
        return

    if changed_jdk8:
        to_list = load_recipients(RECIPIENTS_JDK8_ENV)
        cc_list = load_recipients(CC_RECIPIENTS_JDK8_ENV)
        html = build_email_jdk8(jdk8)
        send_email(html,to_list,cc_list,"Version Update Summary – JDK8 (Tomcat / PostgreSQL)",)
        save_json(JDK8_FILE, jdk8)

    if changed_jdk21:
        to_list = load_recipients(RECIPIENTS_JDK21_ENV)
        cc_list = load_recipients(CC_RECIPIENTS_JDK21_ENV)
        html = build_email_jdk21(jdk21)
        send_email(html,to_list,cc_list,"Version Update Summary – JDK21 (Tomcat / PostgreSQL)",)
        save_json(JDK21_FILE, jdk21)

    print("Done.")

if __name__ == "__main__":
    process()
