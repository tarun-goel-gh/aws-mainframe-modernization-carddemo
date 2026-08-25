import os
import zipfile

docs_root = './bob-z-app-docs'
flat_zip_path = './bob-z-app-docs-flat.zip'

seen = {}
with zipfile.ZipFile(flat_zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(docs_root):
        rel_dir = os.path.relpath(root, docs_root)
        for f in files:
            full_p = os.path.join(root, f)
            if rel_dir == '.':
                arc_name = f
            else:
                prefix = rel_dir.replace('\\', '__').replace('/', '__')
                arc_name = f"{prefix}__{f}" if f in seen else f
            
            seen[arc_name] = seen.get(arc_name, 0) + 1
            z.write(full_p, arc_name)

size_mb = os.path.getsize(flat_zip_path) / (1024 * 1024)
print(f"Flat Zip Created: {os.path.abspath(flat_zip_path)}")
print(f"Total Files (flat, zero subfolders): {len(seen)}")
print(f"Size: {size_mb:.2f} MB")
