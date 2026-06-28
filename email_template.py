
TABLE_STYLE = """
<style>
body{
    font-family:Calibri,Arial,sans-serif;
    font-size:15px;
    color:#222;
}
table{
    border-collapse:collapse;
    width:100%;
    margin:18px 0 40px 0;
}
th{
    background:#173A5E;
    color:white;
    border:2px solid #173A5E;
    padding:10px;
    text-align:center;
    font-size:15px;
    font-weight:bold;
}
td{
    border:1px solid #666;
    background:#F8F8F8;
    padding:10px;
    vertical-align:middle;
}
.center{text-align:center;}
.section{
    font-size:20px;
    font-weight:bold;
    text-decoration:underline;
    margin:18px 0 10px;
}
.comp{font-size:16px;font-weight:bold;}
</style>
"""

ICONS={
    "Apache Tomcat":"🧩",
    "PostgreSQL":"🐘"
}

def build_table(data, show_current=True):
    h=data["headers"]
    html=f'<div class="section">{data["title"]}</div>'
    html+='<table>'
    html+='<tr>'
    html+=f'<th rowspan="2" width="18%">{h["componentName"]}</th>'
    html+=f'<th colspan="{len(h["dsrVersions"])}" width="18%">Component versions in the last release of DSR</th>'
    html+=f'<th rowspan="2" width="16%">{h["latestComponentVersion"]}</th>'
    html+=f'<th rowspan="2" width="16%">{h["releaseDate"]}</th>'
    if show_current:
        html+=f'<th rowspan="2" width="16%">{h["currentComponentVersion"]}</th>'
    html+=f'<th rowspan="2" width="20%">{h["comments"]}</th></tr><tr>'
    for v in h["dsrVersions"]:
        html+=f'<th>{v}</th>'
    html+='</tr>'
    for c in data["components"]:
        icon=ICONS.get(c["componentName"],"")
        html+='<tr>'
        html+=f'<td class="comp">{icon} {c["componentName"]}</td>'
        for v in h["dsrVersions"]:
            html+=f'<td class="center">{c["dsrVersions"].get(v,"-")}</td>'
        html+=f'<td class="center"><b>{c["latestComponentVersion"]}</b></td>'
        html+=f'<td class="center">{c["releaseDate"]}</td>'
        if show_current:
            html+=f'<td class="center">{c["currentComponentVersion"]}</td>'
        html+=f'<td>{c["comments"]}</td></tr>'
    html+='</table>'
    return html

def build_email(jdk8_data,jdk21_data):
    return f"""
<html>
{TABLE_STYLE}
<body>
<p>Hi Team,</p>
<p>Please find below the version update summary for <b>Apache Tomcat</b> and <b>Postgres</b> components used in <b>DSR</b>.</p>
{build_table(jdk8_data,True)}
{build_table(jdk21_data,False)}
<p>Thanks & Regards,<br><b>Version Monitor Agent</b></p>
</body>
</html>
"""
