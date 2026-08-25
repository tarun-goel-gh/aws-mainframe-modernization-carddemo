#!/usr/bin/env python3
import os, sys, zipfile, re

docs_root = "./bob-z-app-docs"
zip_path = "./bob-z-app-docs-latest.zip"

# Secret patterns checking for actual credentials
PATTERNS = [
    (r"(?i)\bpassword\s*[:=]\s*['\"][a-zA-Z0-9!@#$%^&*()_+=-]{4,}['\"]", "hard-coded password value"),
    (r"(?i)\b(api[_-]?key|secret)\s*[:=]\s*['\"][a-zA-Z0-9!@#$%^&*()_+=-]{10,}['\"]", "API key / secret"),
    (r"-----BEGIN (RSA|EC|OPENSSH )?PRIVATE KEY-----", "embedded private key"),
    (r"(?i)(user\s*id|uid)\s*=.*password\s*=[a-zA-Z0-9]+", "DB2/ODBC connection string with credentials"),
    (r"(?i)bearer\s+[A-Za-z0-9\-_.]{20,}", "bearer token"),
    (r"(?i)jdbc:[a-z0-9]+://[^;]*password=[a-zA-Z0-9]+", "JDBC connection string with embedded password"),
]

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(docs_root):
        for f in files:
            full_p = os.path.join(root, f)
            arc_name = os.path.relpath(full_p, os.path.dirname(docs_root))
            z.write(full_p, arc_name)

hits = []
with zipfile.ZipFile(zip_path, 'r') as z:
    for info in z.infolist():
        if info.is_dir() or info.file_size > 8 * 1024 * 1024:
            continue
        try:
            text = z.read(info).decode("utf-8", "ignore")
        except Exception:
            continue
        for pat, label in PATTERNS:
            if re.search(pat, text):
                hits.append(f"{info.filename}: {label}")

if hits:
    print("LEAK DETECTED:", hits)
    sys.exit(1)
else:
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    file_count = len(zipfile.ZipFile(zip_path).namelist())
    print(f"SUCCESS: {zip_path} created ({size_mb:.2f} MB, {file_count} files)")
    print("Disclosure scan: CLEAN (0 secrets found)")
