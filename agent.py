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

    return soup.select_one("a").text.strip()


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

    <p style="color:gray;">Automated Agent</p>
    </body>
