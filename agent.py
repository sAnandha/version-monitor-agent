import requests
import json
import smtplib
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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

# -------------------------------
# FETCH FUNCTIONS
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
# JSON HELPERS
# -------------------------------

def load_json(file):
    try:
        return json.load(open(file))
    except:
        return {}


def save_json(file, data):
    json.dump(data, open(file, "w"), indent=2)


# -------------------------------
# EMAIL LIST
# -------------------------------

def load_recipients():
    try:
        data = json.load(open(EMAIL_FILE))
        return data.get("recipients", [])
    except:
        return []


# -------------------------------
# TABLE BUILDER
# -------------------------------

def build_table(changes):
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
    <table border="1" style="border-collapse:collapse;margin-bottom:20px;">
        <tr style="background:#e6e6e6;">
            <th>Component</th>
            <th>Previous Version</th>
            <th>Latest Version</th>
        </tr>
        {rows}
    </table>
    """


# -------------------------------
# EMAIL SEND
# -------------------------------

def send_email(html):
    recipients = load_recipients()

    print("Recipients:", recipients)

    if not recipients:
        print("❌ No recipients configured")
        return

    msg = MIMEMultipart("alternative")

    msg["Subject"] = "Version Update Summary – Postgres and Apache Tomcat"
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, recipients, msg.as_string())

    print("✅ Email sent")


# -------------------------------
# MAIN LOGIC
# -------------------------------

def run_agent():
    print("Running agent...")

    latest = {
        "Tomcat 9": get_tomcat9(),
        "Tomcat 11": get_tomcat11(),
        "PostgreSQL": get_postgres()
    }

    print("Latest:", latest)

    jdk8_old = load_json(JDK8_FILE)
    jdk21_old = load_json(JDK21_FILE)

    jdk8_current = {
        "Tomcat 9": latest["Tomcat 9"],
        "PostgreSQL": latest["PostgreSQL"]
    }

    jdk21_current = {
        "Tomcat 11": latest["Tomcat 11"],
        "PostgreSQL": latest["PostgreSQL"]
    }

    print("JDK8 old:", jdk8_old)
    print("JDK8 new:", jdk8_current)
    print("JDK21 old:", jdk21_old)
    print("JDK21 new:", jdk21_current)

    jdk8_changes = {}
    jdk21_changes = {}

    # -------- JDK8 --------
    if not jdk8_old:
        save_json(JDK8_FILE, jdk8_current)
        print("Initialized JDK8")
    else:
        for key in jdk8_current:
            if key in jdk8_old:
                if jdk8_current[key] != jdk8_old[key]:
                    jdk8_changes[key] = {
                        "old": jdk8_old[key],
                        "new": jdk8_current[key]
                    }

    # -------- JDK21 --------
    if not jdk21_old:
        save_json(JDK21_FILE, jdk21_current)
        print("Initialized JDK21")
    else:
        for key in jdk21_current:
            if key in jdk21_old:
                if jdk21_current[key] != jdk21_old[key]:
                    jdk21_changes[key] = {
                        "old": jdk21_old[key],
                        "new": jdk21_current[key]
                    }

    # -------- SEND EMAIL --------
    if jdk8_changes or jdk21_changes:

        html = "<html><body style='font-family:Arial;'>"

        if jdk8_changes:
            html += "<h3>JDK8</h3>"
            html += build_table(jdk8_changes)

        if jdk21_changes:
            html += "<h3>JDK21</h3>"
            html += build_table(jdk21_changes)

        html += "<p>Action: Review release notes and plan upgrade.</p>"
        html += "</body></html>"

        send_email(html)

        # ✅ update JSON AFTER email
        save_json(JDK8_FILE, jdk8_current)
        save_json(JDK21_FILE, jdk21_current)

    else:
        print("✅ No changes detected")


if __name__ == "__main__":
    run_agent()
