
"""
Skeleton agent.py for Version Monitor Agent.

NOTE:
This file is designed to work with the email_template.py you created.
You will need to adjust the JSON field names to exactly match your
versions_jdk8.json and versions_jdk21.json structure.
"""
import json
import os
import re
import smtplib
import requests

from dotenv import load_dotenv
from copy import deepcopy
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()
from email_template import build_email



EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS")

JDK8_FILE = "versions_jdk8.json"
JDK21_FILE = "versions_jdk21.json" 
# EMAIL_FILE = "emails.json" # Uncomment this if you want to use Json based email file

URLS = {
    "Tomcat 9": "https://tomcat.apache.org/download-90.cgi",
    "Tomcat 11": "https://tomcat.apache.org/tomcat-11.0-doc/index.html",
    "Tomcat 9 Changelog": "https://tomcat.apache.org/tomcat-9.0-doc/changelog.html",
    "Tomcat 11 Changelog": "https://tomcat.apache.org/tomcat-11.0-doc/changelog.html",
    "PostgreSQL": "https://www.postgresql.org/docs/release/"
}



def get_tomcat9():
    r = requests.get(URLS["Tomcat 9 Changelog"], timeout=20)
    r.raise_for_status()
    version_match = re.search(r"Version\s+(9\.0\.\d+)",r.text)
    date_match = re.search(r'<time datetime="([^"]+)">',r.text)    
    release_date = datetime.strptime(
        date_match.group(1),"%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")

    return {
        "version": version_match.group(1),
        "release_date": release_date
    }


def get_tomcat11():
    r = requests.get(URLS["Tomcat 11 Changelog"], timeout=20)
    r.raise_for_status()
    version_match = re.search(r"Version\s+(11\.\d+\.\d+)",r.text)
    date_match = re.search(r'<time datetime="([^"]+)">',r.text)
    release_date = datetime.strptime(
        date_match.group(1),"%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")

    return {
        "version": version_match.group(1),
        "release_date": release_date
    }


def get_postgres():
    """Fetch latest release from the banner, e.g. 'June 4, 2026: PostgreSQL 19 Beta 1 Released!'"""
    r = requests.get(URLS["PostgreSQL"], timeout=20)
    r.raise_for_status()
    patterns = [
        r"([A-Za-z]+\s+\d{1,2},\s+\d{4}):\s*<a[^>]*>(PostgreSQL\s+.+?)\s*Released!</a>",
        r"([A-Za-z]+\s+\d{1,2},\s+\d{4}):\s*(PostgreSQL\s+.+?)\s*Released!",
    ]
    for pattern in patterns:
        m = re.search(pattern, r.text)
        if m:
            return {"version": m.group(2).strip(), "release_date": m.group(1).strip()}
    return {"version": "Unknown", "release_date": "Unknown"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_recipients():
    raw = os.getenv("EMAIL_RECIPIENTS", "")
    return [e.strip() for e in raw.split(",") if e.strip()]


def send_email(html):
    recipients = load_recipients()
    if not recipients:
        print("No recipients configured.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Version Update Summary – PostgreSQL and Apache Tomcat"
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.sendmail(EMAIL_USER,recipients,msg.as_string())


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

    if component.get("releaseDate") != release_date:
        component["releaseDate"] = release_date
        changed = True

    return changed


def process():
    jdk8 = load_json(JDK8_FILE)
    jdk21 = load_json(JDK21_FILE)

    original8 = deepcopy(jdk8)
    original21 = deepcopy(jdk21)

    postgres = get_postgres()

    latest = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
        "PostgreSQL": postgres,
    }

    changed = False

    # JDK 8 Components
    for c in jdk8["components"]:
        if c["componentName"] == "Apache Tomcat":
            changed |= update_tomcat_component(c,latest["Tomcat 9"]["version"],latest["Tomcat 9"]["release_date"])

        elif c["componentName"] == "PostgreSQL":
            changed |= update_postgres_component(c,postgres["version"],postgres["release_date"])

    # JDK 21 Components
    for c in jdk21["components"]:
        if c["componentName"] == "Apache Tomcat":
            changed |= update_tomcat_component(c,latest["Tomcat 11"]["version"],latest["Tomcat 11"]["release_date"])

        elif c["componentName"] == "PostgreSQL":
            changed |= update_postgres_component(c,postgres["version"],postgres["release_date"])

    if not changed:
        print("No version changes detected.")
        return

    html = build_email(jdk8, jdk21)
    send_email(html)

    save_json(JDK8_FILE, jdk8)
    save_json(JDK21_FILE, jdk21)

    print("Email sent and JSON updated.")


if __name__ == "__main__":
    process()
