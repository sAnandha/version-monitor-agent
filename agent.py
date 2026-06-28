
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

from copy import deepcopy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email_template import build_email

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

JDK8_FILE = "versions_jdk8.json"
JDK21_FILE = "versions_jdk21.json"
EMAIL_FILE = "emails.json"

URLS = {
    "Tomcat 9": "https://tomcat.apache.org/download-90.cgi",
    "Tomcat 11": "https://tomcat.apache.org/tomcat-11.0-doc/index.html",
    "PostgreSQL": "https://www.postgresql.org/docs/release/"
}


def get_tomcat9():
    r = requests.get(URLS["Tomcat 9"], timeout=20)
    r.raise_for_status()
    m = re.search(r"\b9\.0\.\d+\b", r.text)
    return m.group(0) if m else "Unknown"


def get_tomcat11():
    r = requests.get(URLS["Tomcat 11"], timeout=20)
    r.raise_for_status()
    m = re.search(r"\b11\.\d+\.\d+\b", r.text)
    return m.group(0) if m else "Unknown"


def get_postgres():
    r = requests.get(URLS["PostgreSQL"], timeout=20)
    r.raise_for_status()
    m = re.search(r"PostgreSQL\s+(\d+\.\d+)", r.text)
    return m.group(1) if m else "Unknown"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_recipients():
    data = load_json(EMAIL_FILE)
    return data.get("recipients", [])


def send_email(html):
    recipients = load_recipients()
    if not recipients:
        print("No recipients configured.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Version Update Summary – Postgres and Apache Tomcat"
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.sendmail(EMAIL_USER, recipients, msg.as_string())


def update_component(component, latest_version):
    changed = False
    if component["latestComponentVersion"] != latest_version:
        component["latestComponentVersion"] = latest_version
        changed = True
    return changed


def process():
    jdk8 = load_json(JDK8_FILE)
    jdk21 = load_json(JDK21_FILE)

    original8 = deepcopy(jdk8)
    original21 = deepcopy(jdk21)

    latest = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
        "PostgreSQL": get_postgres()
    }

    changed = False

    for c in jdk8["components"]:
        if c["componentName"] == "Apache Tomcat":
            changed |= update_component(c, latest["Tomcat 9"])
        elif c["componentName"] == "PostgreSQL":
            changed |= update_component(c, latest["PostgreSQL"])

    for c in jdk21["components"]:
        if c["componentName"] == "Apache Tomcat":
            changed |= update_component(c, latest["Tomcat 11"])
        elif c["componentName"] == "PostgreSQL":
            changed |= update_component(c, latest["PostgreSQL"])

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
