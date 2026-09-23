# Dead-hook finder with suggested replacements: python tools/remap.py out.txt YTLite.x Sideloading.x ...
# Prints hooks whose class/method is gone, and the *Impl class or other classes that now implement the method.
import re, sys, collections, os
dump, src = sys.argv[1], sys.argv[2:]
meths, supers, classes, bysel = collections.defaultdict(dict), {}, set(), collections.defaultdict(set)
for line in open(dump, encoding="utf-8"):
    if line.startswith("@class "):
        m = re.match(r"@class (\S+) : (\S+)", line); classes.add(m[1]); supers[m[1]] = m[2]; continue
    m = re.match(r"([^\s(]+)(?:\([^)]*\))? ([-+])(\S+) (\S+)", line)
    if m: meths[m[1]][m[2]+m[3]] = m[4]; bysel[m[2]+m[3]].add(m[1])
def find(cls, key):  # True / False / None(unknown: inherits from system class)
    seen = 0
    while seen < 60:
        if cls not in classes: return None
        if key in meths[cls]: return True
        cls = supers.get(cls, "?"); seen += 1
    return False
def strip_types(s):
    p = None
    while p != s: p = s; s = re.sub(r"\([^()]*\)", "", s)
    return s
def selector(line):
    rest = strip_types(re.sub(r"^[-+]\s*", "", line)).split("{")[0]
    parts = re.findall(r"(\w+)\s*:", rest)
    return "".join(p + ":" for p in parts) if parts else (re.findall(r"\w+", rest) or ["?"])[0]
SYS = re.compile(r"^(UI|NS|AV|CA|WK|MP|SF|PH|CF|MK|GC|LS|SK|_UI)[A-Z_]")
for f in src:
    cls, prev = None, ""
    for n, line in enumerate(open(f, encoding="utf-8", errors="ignore"), 1):
        s = line.strip(); m = re.match(r"%hook\s+([\w.]+)", s)
        if m: cls = m[1]; prev = s; continue
        if s.startswith("%end"): cls = None
        elif cls and re.match(r"^[-+]\s*\(", s) and not prev.startswith("%new") and not SYS.match(cls):
            key = s[0] + selector(s); r = find(cls, key)
            if r is not True and not (r is None and cls in classes):
                impl = cls + "Impl"
                if find(impl, key): verdict = f"-> {impl} (same method)"
                else:
                    others = sorted(bysel.get(key, ()))[:4]
                    verdict = f"-> other classes with it: {others}" if others else "-> NOT FOUND anywhere"
                print(f"{os.path.basename(f)}:{n} {cls} {key} {verdict}")
        if s: prev = s
