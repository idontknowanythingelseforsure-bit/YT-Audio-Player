import sqlite3, os, shutil
profile = os.path.expandvars('%APPDATA%\\Mozilla\\Firefox\\Profiles\\hxamlyw0.default-release')
db_path = os.path.join(profile, 'cookies.sqlite')
if os.path.exists(db_path):
    shutil.copy2(db_path, 'cookies_copy.sqlite')
    conn = sqlite3.connect('cookies_copy.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT host, path, isSecure, isHttpOnly, expiry, name, value FROM moz_cookies WHERE host LIKE '%youtube%'")
    rows = cursor.fetchall()
    conn.close()
    with open('youtube_cookies.txt', 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for host, path, secure, httponly, expiry, name, value in rows:
            f.write(f"{host}\t{'TRUE' if secure else 'FALSE'}\t{path}\t{'TRUE' if httponly else 'FALSE'}\t{expiry}\t{name}\t{value}\n")
    print('Created youtube_cookies.txt with', len(rows), 'cookies')
else:
    print('Firefox profile not found')
