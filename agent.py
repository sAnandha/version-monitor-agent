import requests
from bs4 import BeautifulSoup
import json
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import re

STATE_FILE = "versions.json"

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

URLS = {
    "Tomcat 9": "https://tomcat.apache.org/download-90.cgi",
    "Tomcat 11": "https://tomcat.apache.org/tomcat-11.0-doc/index.html",
    "PostgreSQL": "https://www.postgresql.org/docs/release/"
}

# ----------------------------------
# FETCH FUNCTIONS
# ----------------------------------

def get_tomcat9():
    r = requests.get(URLS["Tomcat 9"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    match = re.search(r"\b9\.0\.\d+\b", soup.text)
    return match.group(0) if match else "Unknown"

def get_tomcat11():
    r = requests.get(URLS["Tomcat 11"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    match = re.search(r"\b11\.\d+\.\d+\b", soup.text)
    return match.group(0) if match else "Unknown"

def get_postgres():
    r = requests.get(URLS["PostgreSQL"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    match = re.search(r"PostgreSQL\s+(\d+\.\d+)", soup.text)
    return match.group(1) if match else "Unknown"


# ----------------------------------
# STATE MANAGEMENT
# ----------------------------------

def load_state():
    try:
        return json.load(open(STATE_FILE))
    except:
        return {
            "JDK8": {},
            "JDK21": {}
        }

def save_state(data):
    json.dump(data, open(STATE_FILE, "w"), indent=2)


# ----------------------------------
# EMAIL TEMPLATE (MATCH SCREENSHOT)
# ----------------------------------

def build_email(changes):
    rows = ""
    for comp, val in changes.items():
        rows += f"""
        <tr>
            <td style="padding:8px;">{comp}</td>
            <td style="padding:8px;">{val['old']}</td>
            <td style="padding:8px;">{val['new']}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial;background:#fff;">

    <h2 style="background:#d9d9d9;padding:6px;">
    Version Update Summary – Postgres and Apache Tomcat
    </h2>

    <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>

    <table border="1" style="border-collapse:collapse;">
        <tr style="background:#d9d9d9;">
            <th style="padding:8px;">Component</th>
            <th style="padding:8px;">Previous Version</th>
            <th style="padding:8px;">Latest Version</th>
        </tr>
        {rows}
    </table>

    <p style="margin-top:10px;">Action: Review release notes and plan upgrade.</p>

    </body>
    </html>
    """


# ----------------------------------
# EMAIL SEND
# ----------------------------------

def send_email(html):
    msg = MIMEMultipart("alternative")

    msg["Subject"] = "Version Update Summary – Postgres and Apache Tomcat"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [EMAIL_USER], msg.as_string())

    print("✅ Email sent")


# ----------------------------------
# MAIN LOGIC
# ----------------------------------

def run_agent():
    print("Agent started...")

    old = load_state()

    new_versions = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
        "PostgreSQL": get_postgres()
    }

    print("NEW:", new_versions)

    # storing versions under JDK8 group (can expand later)
    jdk = "JDK8"

    if jdk not in old:
        old[jdk] = {}

    changes = {}

    for key in new_versions:
        old_val = old[jdk].get(key)

        if old_val and new_versions[key] != oldchanges[key] = {
                "old": old_val,
                "new": new_versions[key]
            }

    # FIRST RUN → initialize only
    if not old[jdk]:
        old[jdk] = new_versions
        save_state(old)
        print("Initial baseline created")
        return

    # SEND MAIL IF CHANGE
    if changes:
        print("Changes detected:", changes)

        html = build_email(changes)
        send_email(html)

        # ✅ UPDATE JSON AFTER MAIL
        old[jdk] = new_versions
        save_state(old)

    else:
        print("No changes detected")


if __name__ == "__main__":
    run_agent()
