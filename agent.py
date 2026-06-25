import requests
from bs4 import BeautifulSoup
import json
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import re

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

FILES = {
    "JDK8": "versions_jdk8.json",
    "JDK21": "versions_jdk21.json"
}

URLS = {
    "Tomcat 9": "https://tomcat.apache.org/download-90.cgi",
    "Tomcat 11": "https://tomcat.apache.org/tomcat-11.0-doc/index.html",
    "PostgreSQL": "https://www.postgresql.org/docs/release/"
}

# -------------------------------
# FETCH
# -------------------------------
def get_tomcat9():
    r = requests.get(URLS["Tomcat 9"], timeout=10)
    match = re.search(r"\b9\.0\.\d+\b", r.text)
    return match.group(0) if match else "Unknown"

def get_tomcat11():
    r = requests.get(URLS["Tomcat 11"], timeout=10)
    match = re.search(r"\b11\.\d+\.\d+\b", r.text)
    return match.group(0) if match else "Unknown"

def get_postgres():
    r = requests.get(URLS["PostgreSQL"], timeout=10)
    match = re.search(r"PostgreSQL\s+(\d+\.\d+)", r.text)
    return match.group(1) if match else "Unknown"

# -------------------------------
# LOAD / SAVE
# -------------------------------
def load_state(file):
    try:
        return json.load(open(file))
    except:
        return {}

def save_state(file, data):
    json.dump(data, open(file, "w"), indent=2)

# -------------------------------
# HTML TABLE
# -------------------------------
def build_table(title, changes):
    if not changes:
        return ""

    rows = ""
    for comp, val in changes.items():
        rows += f"""
        <tr>
            <td>{comp}</td>
            <td>{val['old']}</td>
            <td>{val['new']}</td>
        </tr>
        """

    return f"""
    <h3 style="margin-top:20px;">{title}</h3>
    <table border="1" style="border-collapse:collapse;">
        <tr style="background:#d9d9d9;">
            <th>Component</th>
            <th>Previous Version</th>
            <th>Latest Version</th>
        </tr>
        {rows}
    </table>
    """

# -------------------------------
# EMAIL
# -------------------------------
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

# -------------------------------
# MAIN
# -------------------------------
def run_agent():
    print("Agent started...")

    # Latest versions
    latest = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
        "PostgreSQL": get_postgres()
    }

    all_changes = {}
    email_sections = ""

    # ---------------- JDK8 ----------------
    jdk8_old = load_state(FILES["JDK8"])
    jdk8_changes = {}

    for key in latest:
        if key in jdk8_old and latest[key] != jdk8_old[key]:
            jdk8_changes[key] = {
                "old": jdk8_old[key],
                "new": latest[key]
            }

    # ---------------- JDK21 ----------------
    jdk21_old = load_state(FILES["JDK21"])
    jdk21_changes = {}

    for key in latest:
        if key in jdk21_old and latest[key] != jdk21_old[key]:
            jdk21_changes[key] = {
                "old": jdk21_old[key],
                "new": latest[key]
            }

    # First run initialization
    if not jdk8_old:
        save_state(FILES["JDK8"], latest)
        print("JDK8 initialized")

    if not jdk21_old:
        save_state(FILES["JDK21"], latest)
        print("JDK21 initialized")

    # Build email sections
    email_sections += build_table("JDK8", jdk8_changes)
    email_sections += build_table("JDK21", jdk21_changes)

    # Send email if any change in any group
    if jdk8_changes or jdk21_changes:

        html = f"""
        <html>
        <body style="font-family:Arial;">
        <h2 style="background:#d9d9d9;padding:6px;">
        Version Update Summary – Postgres and Apache Tomcat
        </h2>

        <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>

        {email_sections}

        <p>Action: Review release notes and plan upgrade.</p>
        </body>
        </html>
        """

        send_email(html)

        # ✅ update both JSONs AFTER mail
        save_state(FILES["JDK8"], latest)
        save_state(FILES["JDK21"], latest)

    else:
        print("No changes detected")


if __name__ == "__main__":
    run_agent()
