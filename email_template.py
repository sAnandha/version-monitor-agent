
TABLE_STYLE="""
<style>
body{font-family:Calibri,Arial,sans-serif;font-size:15px;color:#222;}
.section{
font-size:28px;
font-weight:700;
color:#222;
margin:28px 0 14px 0;
text-decoration:underline;
display:block;
width:100%;
clear:both;
}
table{
width:100%;
border-collapse:collapse;
table-layout:fixed;
margin-bottom:35px;
}
th{
background:#173A5E;
color:#fff;
border:2px solid #173A5E;
padding:10px;
font-size:15px;
font-weight:bold;
text-align:center;
vertical-align:middle;
}
td{
border:1px solid #666;
padding:10px;
background:#F7F7F7;
vertical-align:top;
}
.center{text-align:center;}
.comp{font-weight:bold;font-size:16px;}
</style>
"""

ICONS={"Apache Tomcat":"🧩","PostgreSQL":"🐘"}

def build_table(data,show_current=True):
    h=data["headers"]
    html=f'<div class="section">{data["title"]}</div>'
    html+='<table>'
    html+='<tr>'
    html+=f'<th rowspan="2" style="width:16%">{h["componentName"]}</th>'
    html+=f'<th colspan="{len(h["dsrVersions"])}" style="width:18%">Component versions in the last release of DSR</th>'
    html+=f'<th rowspan="2" style="width:16%">{h["latestComponentVersion"]}</th>'
    html+=f'<th rowspan="2" style="width:16%">{h["releaseDate"]}</th>'
    if show_current:
        html+=f'<th rowspan="2" style="width:16%">{h["currentComponentVersion"]}</th>'
    html+=f'<th rowspan="2" style="width:18%">{h["comments"]}</th></tr><tr>'
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
        html+=f'<td>{c["comments"]}</td>'
        html+='</tr>'
    html+='</table>'
    return html

def build_email_jdk8(jdk8_data):
    return f"""<html>{TABLE_STYLE}<body>
<p><b>Hi Team,</b></p>
<p>Please find below the version update summary for <b>JDK8</b> – <b>Apache Tomcat</b> and <b>Postgres</b> components used in <b>DSR</b>.</p>
{build_table(jdk8_data, True)}
<p>Thanks &amp; Regards,<br><b>Version Monitor Agent</b></p>
</body></html>"""


def build_email_jdk21(jdk21_data):
    return f"""<html>{TABLE_STYLE}<body>
<p><b>Hi Team,</b></p>
<p>Please find below the version update summary for <b>JDK21</b> – <b>Apache Tomcat</b> and <b>Postgres</b> components used in <b>DSR</b>.</p>
{build_table(jdk21_data, False)}
<p>Thanks &amp; Regards,<br><b>Version Monitor Agent</b></p>
</body></html>"""
