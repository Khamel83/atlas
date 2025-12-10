import json
import sqlite3
import shutil
import os

cookies_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies")
shutil.copy(cookies_path, "chrome_cookies.db")

conn = sqlite3.connect("chrome_cookies.db")
cursor = conn.cursor()

cursor.execute("SELECT name, value, host_key, path, expires_utc, is_secure FROM cookies WHERE host_key LIKE '%youtube%' OR host_key LIKE '%google%'")
rows = cursor.fetchall()

cookies = []
for name, value, host, path, expires, secure in rows:
    cookies.append({"name": name, "value": value, "domain": host, "path": path, "secure": bool(secure)})

with open("youtube_cookies.json", "w") as f:
    json.dump(cookies, f)

print(f"Exported {len(cookies)} cookies")
os.remove("chrome_cookies.db")
conn.close()
