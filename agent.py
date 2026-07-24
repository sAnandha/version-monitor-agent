
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
    release_date = datetime.strptime(
        date_match.group(1), "%Y-%m-%d"
    ).strftime("%B %d, %Y").replace(" 0", " ")

    return {
        "version": version_match.group(1),
        "release_date": release_date,
    }


def get_tomcat11():
    r = requests.get(URLS["Tomcat 11 Changelog"], timeout=20)
    r.raise_for_status()
    version_match = re.search(r"Version\s+(11\.\d+\.\d+)", r.text)
    date_match = re.search(r'<time datetime="([^"]+)">', r.text)
    release_date = datetime.strptime(
        date_match.group(1), "%Y-%m-%d"
    ).strftime("%B %d, %Y").replace(" 0", " ")

    return {
        "version": version_match.group(1),
        "release_date": release_date,
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

    if component.get("releaseDate") != release_date:
        component["releaseDate"] = release_date
        changed = True

    return changed


def process():
    jdk8 = load_json(JDK8_FILE)
    jdk21 = load_json(JDK21_FILE)

    postgres = get_postgres()

    latest = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
    }

    changed_jdk8 = False
    changed_jdk21 = False

    for c in jdk8["components"]:
        if c["componentName"] == "Apache Tomcat":
            changed_jdk8 |= update_tomcat_component(
                c, latest["Tomcat 9"]["version"], latest["Tomcat 9"]["release_date"]
            )
        elif c["componentName"] == "PostgreSQL":
            changed_jdk8 |= update_postgres_component(
                c, postgres["version"], postgres["release_date"]
            )

    for c in jdk21["components"]:
        if c["componentName"] == "Apache Tomcat":
            changed_jdk21 |= update_tomcat_component(
                c, latest["Tomcat 11"]["version"], latest["Tomcat 11"]["release_date"]
            )
        elif c["componentName"] == "PostgreSQL":
            changed_jdk21 |= update_postgres_component(
                c, postgres["version"], postgres["release_date"]
            )

    if not changed_jdk8 and not changed_jdk21:
        print("No version changes detected.")
        return

    if changed_jdk8:
        to_list = load_recipients(RECIPIENTS_JDK8_ENV)
        cc_list = load_recipients(CC_RECIPIENTS_JDK8_ENV)
        html = build_email_jdk8(jdk8)
        send_email(
            html,
            to_list,
            cc_list,
            "Version Update Summary – JDK8 (Tomcat / PostgreSQL)",
        )
        save_json(JDK8_FILE, jdk8)

    if changed_jdk21:
        to_list = load_recipients(RECIPIENTS_JDK21_ENV)
        cc_list = load_recipients(CC_RECIPIENTS_JDK21_ENV)
        html = build_email_jdk21(jdk21)
        send_email(
            html,
            to_list,
            cc_list,
            "Version Update Summary – JDK21 (Tomcat / PostgreSQL)",
        )
        save_json(JDK21_FILE, jdk21)

    print("Done.")


if __name__ == "__main__":
    process()
