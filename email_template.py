
TABLE_STYLE = """
<style>

body{
    font-family:Calibri,Arial,sans-serif;
    font-size:14px;
}

h2{
    color:#1F4E79;
}

table{
    border-collapse:collapse;
    width:100%;
    margin-bottom:30px;
}

th{
    background:#1F4E79;
    color:white;
    border:1px solid black;
    padding:8px;
    text-align:center;
}

td{
    border:1px solid black;
    padding:8px;
}

.title{
    background:#D9EAD3;
    color:black;
    font-weight:bold;
}

.center{
    text-align:center;
}

</style>
"""


def build_table(data, show_current=True):

    headers = data["headers"]

    html = f"""

<h2>{data['title']}</h2>

<table>

<tr>

<th rowspan="2">{headers['componentName']}</th>

<th colspan="{len(headers['dsrVersions'])}">
Component versions in the last release of DSR
</th>

<th rowspan="2">
{headers['latestComponentVersion']}
</th>

<th rowspan="2">
{headers['releaseDate']}
</th>

"""

    if show_current:

        html += f"""
<th rowspan="2">
{headers['currentComponentVersion']}
</th>
"""

    html += f"""

<th rowspan="2">
{headers['comments']}
</th>

</tr>

<tr>
"""

    for version in headers["dsrVersions"]:

        html += f"""
<th>{version}</th>
"""

    html += "</tr>"

    for component in data["components"]:

        html += "<tr>"

        html += f"""
<td>{component['componentName']}</td>
"""

        for version in headers["dsrVersions"]:

            html += f"""
<td class='center'>
{component['dsrVersions'].get(version,"-")}
</td>
"""

        html += f"""

<td class='center'>
<b>{component['latestComponentVersion']}</b>
</td>

<td class='center'>
{component['releaseDate']}
</td>

"""

        if show_current:

            html += f"""
<td class='center'>
{component['currentComponentVersion']}
</td>
"""

        html += f"""
<td>
{component['comments']}
</td>
"""

        html += "</tr>"

    html += "</table>"

    return html


def build_email(jdk8_data, jdk21_data):
    html = f"""

<html>

{TABLE_STYLE}

<body>

<p>Hi Team,</p>

<p>
Please find below the version update summary for
<b>Apache Tomcat</b> and <b>Postgres</b> components used in <b>DSR</b>.
</p>

{build_table(jdk8_data,True)}

<br>

{build_table(jdk21_data,False)}

<p>

Regards<br>

<b>Version Monitor Agent</b>

</p>

</body>

</html>

"""

    return html
