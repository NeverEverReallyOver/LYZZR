
import sys
import os

print(f"Executable: {sys.executable}")
print("Sys Path:")
for p in sys.path:
    print(f"  {p}")

site_packages = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages')
print(f"\nGuessed site-packages: {site_packages}")

if os.path.exists(site_packages):
    print("  [OK] Exists")
    
    p1 = os.path.join(site_packages, 'pywin32_system32')
    p2 = os.path.join(site_packages, 'win32')
    p3 = os.path.join(site_packages, 'win32', 'lib')
    
    for p in [p1, p2, p3]:
        print(f"  Checking {p}: {'Found' if os.path.exists(p) else 'MISSING'}")
        if os.path.exists(p):
            try:
                files = os.listdir(p)
                print(f"    Contains {len(files)} files. First few: {files[:3]}")
            except:
                pass
else:
    print("  [ERR] Does not exist")

try:
    import pywintypes
    print("\nSUCCESS: import pywintypes")
except ImportError as e:
    print(f"\nFAILURE: import pywintypes: {e}")
