from fastapi.responses import HTMLResponse


def render_dashboard(queue_stats: dict, recent: list[str]) -> HTMLResponse:
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in queue_stats.items())
    recents = "".join(f"<li>{item}</li>" for item in recent) or "<li>Idle</li>"
    html = f"""
    <html>
      <head><title>Atlas vOS Dashboard</title></head>
      <body>
        <h1>Atlas vOS Dashboard</h1>
        <h2>Queue</h2>
        <table border="1">
          <tr><th>Stage</th><th>Count</th></tr>
          {rows}
        </table>
        <h2>Recent Activity</h2>
        <ul>{recents}</ul>
      </body>
    </html>
    """
    return HTMLResponse(html)
