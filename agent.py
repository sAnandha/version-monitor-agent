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
    "Tomcat 9 Download": "https://tomcat.apache.org/download-90.cgi",
    "Tomcat 11 Changelog": "https://tomcat.apache.org/tomcat-11.0-doc/changelog.html",
    "Tomcat 11 Download": "https://tomcat.apache.org/download-110.cgi",
    "Tomcat Home": "https://tomcat.apache.org/",
    "PostgreSQL": "https://www.postgresql.org/docs/release/",
}

_tomcat_homepage_html = None

def tomcat_version_key(version_str):
    parts = version_str.strip().split(".")
    return tuple(int(p) for p in parts)

def _format_release_date(date_str):
    release_date = datetime.strptime(date_str, "%Y-%m-%d")
    return release_date.strftime("%B %d, %Y").replace(" 0", " ")

def _parse_flexible_release_date(raw):
    value = raw.strip()
    for fmt in (
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%B %d, %Y").replace(" 0", " ")
        except ValueError:
            continue
    return None

def get_tomcat_date_from_changelog_body(html_text, version):
    """Find a release date for a specific version in changelog section headers."""
    if not html_text:
        return None

    escaped = re.escape(version)
    patterns = [
        rf"(\d{{4}}-\d{{2}}-\d{{2}})\s+Tomcat\s+{escaped}\b",
        rf"<h3[^>]*>\s*(\d{{4}}-\d{{2}}-\d{{2}})\s+Tomcat\s+{escaped}\b",
        rf"Tomcat\s+{escaped}.*?<time datetime=\"(\d{{4}}-\d{{2}}-\d{{2}})\">",
    ]

    for pattern in patterns:
        match = re.search(pattern, html_text, re.I | re.S)
        if not match:
            continue
        try:
            return _format_release_date(match.group(1))
        except ValueError:
            continue
    return None

def get_tomcat_date_from_homepage(html_text, version):
    """Find the release date for a version on the Tomcat homepage."""
    if not html_text:
        return None

    escaped = re.escape(version)
    release_block = re.search(
        rf'<h3[^>]*\bid="Tomcat_{escaped}_Released"[^>]*>(.*?)</h3>',
        html_text,
        re.I | re.S,
    )
    if release_block:
        span_date = re.search(
            r'<span[^>]*>(\d{4}-\d{2}-\d{2})</span>',
            release_block.group(1),
            re.I,
        )
        if span_date:
            try:
                return _format_release_date(span_date.group(1))
            except ValueError:
                pass

    patterns = [
        rf"<span[^>]*>(\d{{4}}-\d{{2}}-\d{{2}})</span>\s*Tomcat\s+{escaped}\b",
        rf"(\d{{4}}-\d{{2}}-\d{{2}})</span>\s*Tomcat\s+{escaped}\b",
        rf"(\d{{4}}-\d{{2}}-\d{{2}})\s+Tomcat\s+{escaped}\b",
        rf"Tomcat\s+{escaped}\b[^<]{{0,120}}<span[^>]*>(\d{{4}}-\d{{2}}-\d{{2}})</span>",
        rf"(\d{{4}}-\d{{2}}-\d{{2}})[^<]{{0,120}}{escaped}",
        rf"{escaped}[^<]{{0,120}}(\d{{4}}-\d{{2}}-\d{{2}})",
    ]

    for pattern in patterns:
        match = re.search(pattern, html_text, re.I | re.S)
        if not match:
            continue
        parsed = _parse_flexible_release_date(match.group(1))
        if parsed:
            return parsed
    return None

def resolve_tomcat_release_date(
    version,changelog_html,homepage_html,changelog_header_date=None,stored_release_date=None,
    label="Tomcat",):
    """
    Resolve release date for a version. Priority (vendor updates homepage first):
    homepage -> changelog body -> changelog header -> stored JSON -> Unknown """

    home_date = get_tomcat_date_from_homepage(homepage_html, version)
    if home_date:
        print(f"{label} {version}: release date from Tomcat homepage.")
        return home_date

    body_date = get_tomcat_date_from_changelog_body(changelog_html, version)
    if body_date:
        print(f"{label} {version}: release date from changelog body.")
        return body_date

    if changelog_header_date:
        print(f"{label} {version}: release date from changelog header.")
        return changelog_header_date

    if stored_release_date:
        print(f"{label} {version}: release date unknown; keeping stored date.")
        return stored_release_date

    print(f"{label} {version}: release date unknown.")
    return "Unknown"

def _build_tomcat_result(version,changelog_html,homepage_html,changelog_header_date=None,stored_release_date=None,
    label="Tomcat",):
    return {
        "version": version,
        "release_date": resolve_tomcat_release_date(
            version,changelog_html,
            homepage_html,changelog_header_date=changelog_header_date,
            stored_release_date=stored_release_date,
            label=label,),
    }

def get_tomcat_from_changelog(html_text, major_prefix):
    """Parse latest version and release date from the changelog header block."""
    if not html_text:
        return None

    block = re.search(
        rf"Version\s+({major_prefix}\.\d+\.\d+).*?"
        r'<time datetime="(\d{4}-\d{2}-\d{2})">',
        html_text,
        re.I | re.S,
    )
    if block:
        try:
            return {
                "version": block.group(1),
                "release_date": _format_release_date(block.group(2)),
            }
        except ValueError:
            pass

    version_match = re.search(rf"Version\s+({major_prefix}\.\d+\.\d+)", html_text)
    date_match = re.search(r'<time datetime="([^"]+)">', html_text)
    if not version_match or not date_match:
        return None

    try:
        return {
            "version": version_match.group(1),
            "release_date": _format_release_date(date_match.group(1)),
        }
    except ValueError:
        return None

def get_tomcat_from_download(html_text, major_prefix):
    """Parse the highest advertised version from the Tomcat download page."""
    if not html_text:
        return None

    heading = re.search(rf"<h3[^>]*>\s*({major_prefix}\.\d+\.\d+)\s*</h3>",html_text,re.I,)
    if heading:
        return heading.group(1)

    versions = re.findall(rf"\b({major_prefix}\.\d+\.\d+)\b", html_text)
    if not versions:
        return None

    return max(versions, key=tomcat_version_key)

def resolve_tomcat_version(
    changelog_result,download_version,
    label,changelog_html=None,homepage_html=None,stored_release_date=None,):
    """Prefer the newer version between changelog and download; always reconcile date."""
    if not changelog_result and not download_version:
        print(f"{label} version could not be resolved.")
        return None

    versions = []
    if changelog_result:
        versions.append(changelog_result["version"])
    if download_version:
        versions.append(download_version)

    final_version = max(versions, key=tomcat_version_key)

    if download_version and not changelog_result:
        print(
            f"{label}: using download page version {download_version} "
            "(changelog unavailable).")
    elif (
        changelog_result
        and download_version
        and tomcat_version_key(download_version)
        > tomcat_version_key(changelog_result["version"])):
        print(
            f"{label}: download page has newer version {download_version} "
            f"(changelog still {changelog_result['version']}).")

    changelog_header_date = (
        changelog_result["release_date"]
        if changelog_result and changelog_result["version"] == final_version
        else None
    )

    return _build_tomcat_result(
        final_version,
        changelog_html,
        homepage_html,
        changelog_header_date=changelog_header_date,
        stored_release_date=stored_release_date,
        label=label,
    )

def _fetch_tomcat_page(url, label):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except requests.exceptions.RequestException as exc:
        print(f"{label} fetch failed: {exc}")
        return None

def _get_tomcat_homepage_html():
    global _tomcat_homepage_html
    if _tomcat_homepage_html is None:
        _tomcat_homepage_html = _fetch_tomcat_page(
            URLS["Tomcat Home"],
            "Tomcat homepage",
        )
    return _tomcat_homepage_html

def _get_tomcat(major_prefix, changelog_url, download_url, label, stored_release_date=None):
    changelog_html = _fetch_tomcat_page(changelog_url, f"{label} changelog")
    download_html = _fetch_tomcat_page(download_url, f"{label} download page")
    homepage_html = _get_tomcat_homepage_html()

    changelog_result = get_tomcat_from_changelog(changelog_html, major_prefix)
    download_version = get_tomcat_from_download(download_html, major_prefix)

    return resolve_tomcat_version(
        changelog_result,
        download_version,
        label,
        changelog_html=changelog_html,
        homepage_html=homepage_html,
        stored_release_date=stored_release_date,
    )

def get_tomcat9(stored_release_date=None):
    return _get_tomcat(
        "9",
        URLS["Tomcat 9 Changelog"],
        URLS["Tomcat 9 Download"],
        "Tomcat 9",
        stored_release_date=stored_release_date,
    )

def get_tomcat11(stored_release_date=None):
    return _get_tomcat(
        "11",
        URLS["Tomcat 11 Changelog"],
        URLS["Tomcat 11 Download"],
        "Tomcat 11",
        stored_release_date=stored_release_date,
    )

def _find_component(components, name):
    for component in components:
        if component["componentName"] == name:
            return component
    return None

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
    """Return (notify, updated). Email only when the version changes."""
    version_changed = component["latestComponentVersion"] != version
    date_changed = component.get("releaseDate") != release_date

    if version_changed:
        component["latestComponentVersion"] = version
    if date_changed:
        component["releaseDate"] = release_date

    return version_changed, version_changed or date_changed

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

    tomcat8 = _find_component(jdk8["components"], "Apache Tomcat")
    tomcat21 = _find_component(jdk21["components"], "Apache Tomcat")

    latest = {
        "Tomcat 9": get_tomcat9(
            stored_release_date=tomcat8.get("releaseDate") if tomcat8 else None,
        ),
        "Tomcat 11": get_tomcat11(
            stored_release_date=tomcat21.get("releaseDate") if tomcat21 else None,
        ),
    }

    notify_jdk8 = False
    notify_jdk21 = False
    updated_jdk8 = False
    updated_jdk21 = False

    for c in jdk8["components"]:
        component_fetch_ok = False
        if c["componentName"] == "Apache Tomcat":
            if latest["Tomcat 9"] is not None:
                notify, updated = update_tomcat_component(
                    c,
                    latest["Tomcat 9"]["version"],
                    latest["Tomcat 9"]["release_date"],
                )
                notify_jdk8 |= notify
                updated_jdk8 |= updated
                component_fetch_ok = True
        elif c["componentName"] == "PostgreSQL" and pg_html:
            postgres = resolve_postgres_version(pg_html,pg_date,c["latestComponentVersion"],
                get_last_major_version(c),
                get_latest_beta_version(c),
            )
            postgres_notify = update_postgres_component(
                c,postgres["version"],postgres["release_date"],postgres.get("banner_beta"),)
            notify_jdk8 |= postgres_notify
            updated_jdk8 |= postgres_notify
            component_fetch_ok = True

        if component_fetch_ok:
            status_changed = update_component_status(c, include_current=True)
            notify_jdk8 |= status_changed
            updated_jdk8 |= status_changed

    for c in jdk21["components"]:
        component_fetch_ok = False

        if c["componentName"] == "Apache Tomcat":
            if latest["Tomcat 11"] is not None:
                notify, updated = update_tomcat_component(
                    c,
                    latest["Tomcat 11"]["version"],
                    latest["Tomcat 11"]["release_date"],
                )
                notify_jdk21 |= notify
                updated_jdk21 |= updated
                component_fetch_ok = True
        elif c["componentName"] == "PostgreSQL" and pg_html:
            postgres = resolve_postgres_version(
                pg_html,pg_date,c["latestComponentVersion"],
                get_last_major_version(c),
                get_latest_beta_version(c),
            )
            postgres_notify = update_postgres_component(
                c,postgres["version"],postgres["release_date"],postgres.get("banner_beta"),)
            notify_jdk21 |= postgres_notify
            updated_jdk21 |= postgres_notify
            component_fetch_ok = True

        if component_fetch_ok:
            status_changed = update_jdk21_component_status(c)
            notify_jdk21 |= status_changed
            updated_jdk21 |= status_changed

    if not updated_jdk8 and not updated_jdk21:
        print("No changes detected.")
        return

    if notify_jdk8:
        to_list = load_recipients(RECIPIENTS_JDK8_ENV)
        cc_list = load_recipients(CC_RECIPIENTS_JDK8_ENV)
        html = build_email_jdk8(jdk8)
        send_email(html,to_list,cc_list,"Version Update Summary – JDK8 (Tomcat / PostgreSQL)",)

    if updated_jdk8:
        save_json(JDK8_FILE, jdk8)

    if notify_jdk21:
        to_list = load_recipients(RECIPIENTS_JDK21_ENV)
        cc_list = load_recipients(CC_RECIPIENTS_JDK21_ENV)
        html = build_email_jdk21(jdk21)
        send_email(html,to_list,cc_list,"Version Update Summary – JDK21 (Tomcat / PostgreSQL)",)

    if updated_jdk21:
        save_json(JDK21_FILE, jdk21)

    print("Done.")

if __name__ == "__main__":
    process()
