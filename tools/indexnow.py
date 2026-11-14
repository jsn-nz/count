"""Tell Bing/Yandex (IndexNow) which URLs changed.

Run AFTER the change is live on count.co.nz:
    python3 tools/indexnow.py            # URLs whose content changed in the last generate run
    python3 tools/indexnow.py --all      # every URL in sitemap.xml
    python3 tools/indexnow.py --dry-run  # print what would be sent

The key is the <key>.txt file in the repo root (already served at
https://count.co.nz/<key>.txt). Google does not use IndexNow; it reads the
sitemap, whose lastmod dates generate.py keeps honest.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "count.co.nz"

keys = [f for f in ROOT.glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}", f.stem)]
if len(keys) != 1:
    sys.exit("Expected exactly one IndexNow key file in the repo root, found %d" % len(keys))
key = keys[0].stem
if keys[0].read_text().strip() != key:
    sys.exit("Key file contents do not match its name")

if "--all" in sys.argv:
    urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "sitemap.xml").read_text())
else:
    f = ROOT / "tools" / "changed-urls.txt"
    urls = f.read_text().split() if f.exists() else []
if not urls:
    sys.exit("Nothing to submit.")

print("%d URLs, e.g. %s" % (len(urls), urls[0]))
if "--dry-run" in sys.argv:
    sys.exit(0)

body = json.dumps({"host": HOST, "key": key,
                   "keyLocation": "https://%s/%s.txt" % (HOST, key),
                   "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
with urllib.request.urlopen(req, timeout=30) as r:
    print("IndexNow responded %d (200/202 = accepted)" % r.status)
