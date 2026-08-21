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
    try:
        r = requests.get(URLS["Tomcat 9 Changelog"], timeout=20)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"Tomcat 9 fetch failed: {exc}")
        return None

    version_match = re.search(r"Version\s+(9\.\d+\.\d+)", r.text)
    date_match = re.search(r'<time datetime="([^"]+)">', r.text)

    if not version_match or not date_match:
        print("Tomcat 9 version/date pattern not found.")
        return None

    try:
        release_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
    except ValueError:
        print("Tomcat 9 invalid date format.")
        return None

    return {
        "version": version_match.group(1),
        "release_date": release_date.strftime("%B %d, %Y").replace(" 0", " "),
    }

def get_tomcat11():
    try:
        r = requests.get(URLS["Tomcat 11 Changelog"], timeout=20)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"Tomcat 11 fetch failed: {exc}")
        return None

    version_match = re.search(r"Version\s+(11\.\d+\.\d+)", r.text)
    date_match = re.search(r'<time datetime="([^"]+)">', r.text)

    if not version_match or not date_match:
        print("Tomcat 11 version/date pattern not found.")
        return None

    try:
        release_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
    except ValueError:
        print("Tomcat 11 invalid date format.")
        return None

    return {
        "version": version_match.group(1),
        "release_date": release_date.strftime("%B %d, %Y").replace(" 0", " "),
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

def get_latest_beta_version(component):
    if component.get("latestBetaVersion"):
        return component["latestBetaVersion"]
    stored = component["latestComponentVersion"]
    if is_beta_version(stored):
        return stored.replace("PostgreSQL", "").strip()
    return "0 Beta 0"

def fetch_postgres_banner():
    r = requests.get(URLS["PostgreSQL"], timeout=20)
    r.raise_for_status()
    date_match = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4}):\s*.*?PostgreSQL\s+.+?\s*Released!",r.text,re.I | re.S,)
    release_date = date_match.group(1).strip() if date_match else "Unknown"
    return r.text, release_date

def resolve_postgres_version(
    html_text,release_date,stored_version=None,last_major_version=None,latest_beta_version=None,):
    """
    1. New major in banner > lastMajorVersion -> track major
    2. Else new beta in banner > latestBetaVersion -> track beta
    3. Else keep stored (same banner next day -> no update)
    """
    all_versions = parse_postgres_versions(html_text)
    if not all_versions:
        return {
            "version": stored_version or "Unknown",
            "release_date": release_date,
            "banner_beta": None,
        }

    finals = [v for v in all_versions if not is_beta_version(v)]
    betas = [v for v in all_versions if is_beta_version(v)]
    highest_final = max(finals, key=postgres_version_key) if finals else None
    highest_beta = max(betas, key=postgres_version_key) if betas else None

    last_major_key = postgres_version_key(last_major_version or "0.0")
    latest_beta_key = postgres_version_key(latest_beta_version or "0 Beta 0")

    if highest_final and postgres_version_key(highest_final) > last_major_key:
        return {
            "version": format_postgres_version(highest_final),
            "release_date": release_date,
            "banner_beta": highest_beta,
        }

    if highest_beta and postgres_version_key(highest_beta) > latest_beta_key:
        return {
            "version": format_postgres_version(highest_beta),
            "release_date": release_date,
            "banner_beta": highest_beta,
        }

    return {
        "version": stored_version,
        "release_date": release_date,
        "banner_beta": highest_beta,
    }

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

def normalize_component_version(component_name, version_str):
    v = version_str.strip()
    if component_name == "PostgreSQL":
        return v.replace("PostgreSQL", "").strip()
    return v

def dsr_versions_match_latest(component):
    latest = normalize_component_version(component["componentName"],component["latestComponentVersion"],)
    dsr_values = list(component.get("dsrVersions", {}).values())
    if not dsr_values:
        return False
    return all(
        normalize_component_version(component["componentName"], v) == latest
        for v in dsr_values
    )

def update_component_status(component, include_current=True):
    """Set comments and currentComponentVersion from DSR vs latest comparison."""
    changed = False
    name = component["componentName"]
    latest = component["latestComponentVersion"]

    if dsr_versions_match_latest(component):
        if name == "Apache Tomcat":
            new_comment = f"Tomcat version upgraded to {latest}"
        else:
            new_comment = f"PostgreSQL version upgraded to {latest}"
        new_current = "No Changes"
    else:
        new_comment = "Will discuss with Team for version upgrade"
        new_current = "TBD"

    if component.get("comments") != new_comment:
        component["comments"] = new_comment
        changed = True

    if include_current and "currentComponentVersion" in component:
        if component["currentComponentVersion"] != new_current:
            component["currentComponentVersion"] = new_current
            changed = True

    return changed

def update_jdk21_component_status(component):
    """Set JDK21 comments from DSR vs latest comparison."""
    changed = False
    name = component["componentName"]

    if dsr_versions_match_latest(component):
        if name == "Apache Tomcat":
            new_comment = "Already Upto Date"
        else:
            bare = normalize_component_version(name, component["latestComponentVersion"])
            new_comment = (
                f"We have already upgraded to PostgreSQL v{bare} in AWL21-JDK branch."
            )
    elif name == "Apache Tomcat":
        new_comment = "Will discuss with Team for version upgrade."
    else:
        new_comment = (
            "Need to analyse the impact of latest released version on DSR. "
            "Then will discuss with Team for version upgrade."
        )

    if component.get("comments") != new_comment:
        component["comments"] = new_comment
        changed = True

    return changed

def update_tomcat_component(component, version, release_date):
    changed = False

    if component["latestComponentVersion"] != version:
        component["latestComponentVersion"] = version
        changed = True

    if component.get("releaseDate") != release_date:
        component["releaseDate"] = release_date
        changed = True

    return changed

def update_postgres_component(component, version, release_date, banner_beta=None):
    changed = False
    old_version = component["latestComponentVersion"]

    if component["latestComponentVersion"] != version:
        component["latestComponentVersion"] = version
        changed = True

    if not is_beta_version(version):
        bare = version.replace("PostgreSQL", "").strip()
        if component.get("lastMajorVersion") != bare:
            component["lastMajorVersion"] = bare
            changed = True

    if is_beta_version(version):
        bare = version.replace("PostgreSQL", "").strip()
        if component.get("latestBetaVersion") != bare:
            component["latestBetaVersion"] = bare
            changed = True

    if (
        banner_beta and not is_beta_version(version)
        and component["latestComponentVersion"] != old_version
        and postgres_version_key(banner_beta)
        > postgres_version_key(component.get("latestBetaVersion", "0 Beta 0"))):
        bare_beta = banner_beta.replace("PostgreSQL", "").strip()         
        component["latestBetaVersion"] = bare_beta
        changed = True

    if component.get("releaseDate") != release_date:
        component["releaseDate"] = release_date
        changed = True

    return changed

def process():
    jdk8 = load_json(JDK8_FILE)
    jdk21 = load_json(JDK21_FILE)

    try:
        pg_html, pg_date = fetch_postgres_banner()
    except requests.exceptions.RequestException as exc:
        print(f"PostgreSQL fetch failed: {exc}")
        pg_html, pg_date = None, "Unknown"

    latest = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
    }

    changed_jdk8 = False
    changed_jdk21 = False

    for c in jdk8["components"]:
        component_fetch_ok = False
        if c["componentName"] == "Apache Tomcat":
            if latest["Tomcat 9"] is not None:
                changed_jdk8 |= update_tomcat_component(
                    c,latest["Tomcat 9"]["version"],latest["Tomcat 9"]["release_date"],)
                component_fetch_ok = True
        elif c["componentName"] == "PostgreSQL" and pg_html:
            postgres = resolve_postgres_version(pg_html,pg_date,c["latestComponentVersion"],
                get_last_major_version(c),
                get_latest_beta_version(c),
            )
            changed_jdk8 |= update_postgres_component(
                c,postgres["version"],postgres["release_date"],postgres.get("banner_beta"),)
            component_fetch_ok = True

        if component_fetch_ok:
            changed_jdk8 |= update_component_status(c, include_current=True)

    for c in jdk21["components"]:
        component_fetch_ok = False

        if c["componentName"] == "Apache Tomcat":
            if latest["Tomcat 11"] is not None:
                changed_jdk21 |= update_tomcat_component(c,latest["Tomcat 11"]["version"],latest["Tomcat 11"]["release_date"],)
                component_fetch_ok = True
        elif c["componentName"] == "PostgreSQL" and pg_html:
            postgres = resolve_postgres_version(
                pg_html,pg_date,c["latestComponentVersion"],
                get_last_major_version(c),
                get_latest_beta_version(c),
            )
            changed_jdk21 |= update_postgres_component(c,postgres["version"],postgres["release_date"],postgres.get("banner_beta"),)
            component_fetch_ok = True

        if component_fetch_ok:
            changed_jdk21 |= update_jdk21_component_status(c)

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
