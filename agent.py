import requests
from bs4 import BeautifulSoup
import json
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

STATE_FILE = "versions.json"

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

URLS = {
    "Tomcat 9": "https://tomcat.apache.org/download-90.cgi",
    "Tomcat 11": "https://tomcat.apache.org/tomcat-11.0-doc/index.html",
    "PostgreSQL": "https://www.postgresql.org/docs/release/"
}

# -------------------------------
# FETCH FUNCTIONS
# -------------------------------
def get_tomcat9():
    r = requests.get(URLS["Tomcat 9"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    for line in soup.get_text().split("\n"):
        if "Latest stable release" in line:
            return line.strip().split()[-1]
    return "Unknown"


def get_tomcat11():
    r = requests.get(URLS["Tomcat 11"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.find("title").text
    return title.split("(")[-1].replace(")", "").strip()


def get_postgres():
    r = requests.get(URLS["PostgreSQL"], timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    link = soup.select_one("a")
    if link:
        return link.text.strip()
    return "Unknown"


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
    <h2>🚀 Version Update Alert</h2>
    <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}</p>

    <table border="1" cellpadding="8" cellspacing="0">
        <tr style="background:#eee;">
            <th>Component</th>
            <th>Previous</th>
            <th>Latest</th>
            <th>Status</th>
        </tr>
        {rows}
    </table>

    <p>Action: Review and plan upgrade if required.</p>
    </body>
    </html>
    """


# -------------------------------
# EMAIL SENDER
# -------------------------------
def send_email(html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[ALERT] Version Update - {datetime.now().date()}"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [EMAIL_USER], msg.as_string())


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
            if new[key] != old[key]:   # ✅ FIXED LINE
                changes[key] = {
                    "old": old[key],
                    "new": new[key]
                }

    if not old:
        save_state(new)
        print("Initial run complete")
        return

    if changes:
        print("Changes detected:", changes)
        html = build_email(changes)
        send_email(html)
    else:
        print("No changes detected")

    save_state(new)


if __name__ == "__main__":
    run_agent()
