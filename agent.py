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

# -------------------------------
# FETCH FUNCTIONS (IMPROVED)
# -------------------------------

def get_tomcat9():
    r = requests.get(URLS["Tomcat 9"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    # ✅ Extract version like 9.0.119
    match = re.search(r"\b9\.0\.\d+\b", soup.text)
    return match.group(0) if match else "Unknown"


def get_tomcat11():
    r = requests.get(URLS["Tomcat 11"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.text

    match = re.search(r"\b11\.\d+\.\d+\b", text)
    return match.group(0) if match else "Unknown"


def get_postgres():
    r = requests.get(URLS["PostgreSQL"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.text

    match = re.search(r"PostgreSQL\s+(\d+\.\d+)", text)
    return match.group(1) if match else "Unknown"


# -------------------------------
# STATE MANAGEMENT
# -------------------------------
def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -------------------------------
# EMAIL BUILDER
# -------------------------------
def build_email(changes):
    rows = ""
    for comp, val in changes.items():
        rows += f"""
        <tr>
            <td>{comp}</td>
            <td>{val['old']}</td>
            <td>{val['new']}</td>
            <td style='color:red;font-weight:bold;'>UPDATED</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial;">
    <h2>Version Update Summary – Postgres and Apache Tomcat</h2>

    <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>

    <table border="1" cellpadding="8" cellspacing="0">
        <tr style="background:#eee;">
            <th>Component</th>
            <th>Previous Version</th>
            <th>Latest Version</th>
            <th>Status</th>
        </tr>
        {rows}
    </table>

    <p>Action: Review release notes and plan upgrade.</p>
    </body>
    </html>
    """


# -------------------------------
# EMAIL SENDER
# -------------------------------
def send_email(html):
    msg = MIMEMultipart("alternative")

    msg["Subject"] = "Version Update Summary – Postgres and Apache Tomcat"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [EMAIL_USER], msg.as_string())
            print("✅ Email sent successfully")

    except Exception as e:
        print("❌ Email failed:", str(e))


# -------------------------------
# MAIN LOGIC
# -------------------------------
def run_agent():
    print("Agent started...")

    old = load_state()
    print("OLD:", old)

    new = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
        "PostgreSQL": get_postgres()
    }

    print("NEW:", new)

    changes = {}

    for key in new:
        if key in old:
            if new[key] != old[key]:
                changes[key] = {
                    "old": old[key],
                    "new": new[key]
                }

    if not old:
        save_state(new)
        print("Initial run complete")
        return

    if changes:
        print("✅ Changes detected:", changes)
        html = build_email(changes)
        send_email(html)
    else:
        print("✅ No changes detected")

    save_state(new)


if __name__ == "__main__":
    run_agent()
