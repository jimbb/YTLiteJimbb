# Crash audit: KVC ivars, header-declared YouTube methods and class lookups that no longer exist.
# python tools/crash_audit.py out.txt .   (then filter out %new/tweak-added methods by hand)
import re, sys, collections, glob, os
dump, root = sys.argv[1], sys.argv[2]
meths, supers, classes, ivars, allivars, allsels = collections.defaultdict(set), {}, set(), collections.defaultdict(set), set(), set()
for line in open(dump, encoding="utf-8"):
    if line.startswith("@class "):
        m = re.match(r"@class (\S+) : (\S+)", line); classes.add(m[1]); supers[m[1]] = m[2]; continue
    m = re.match(r"([^\s(]+) ivar (\S+)", line)
    if m: ivars[m[1]].add(m[2]); allivars.add(m[2]); continue
    m = re.match(r"([^\s(]+)(?:\([^)]*\))? ([-+])(\S+) ", line)
    if m: meths[m[1]].add(m[2] + m[3]); allsels.add(m[3])
def chain(c):
    out, n = [], 0
    for cand in (c, c + "Impl"):
        x = cand
        while x in classes and n < 80: out.append(x); x = supers.get(x, "?"); n += 1
    return out
def has_method(c, key): return any(key in meths[x] for x in chain(c))
def has_ivar(c, name): return any(name in ivars[x] for x in chain(c))
SYS = re.compile(r"^(UI|NS|AV|CA|WK|MP|SF|PH|CF|MK|GC|LS|SK|_UI|CL)[A-Z_]")
src = [f for f in glob.glob(os.path.join(root, "**", "*.*"), recursive=True) if re.search(r"\.(x|xm|h|m)$", f) and "protobuf" not in f]
print("=== (a) KVC / ivar access")
for f in src:
    cls = None
    for n, line in enumerate(open(f, encoding="utf-8", errors="ignore"), 1):
        m = re.match(r"\s*%hook\s+(\w+)", line)
        if m: cls = m[1]
        if line.strip().startswith("%end"): cls = None
        for m in re.finditer(r"(\w+|\])\s+(?:valueForKey|setValue:[^\]]*?forKey):@\"(_?\w+)\"", line):
            recv, name = m[1], m[2]
            if recv == "self" and cls and not SYS.match(cls) and (cls in classes or cls + "Impl" in classes):
                ok = has_ivar(cls, name) or has_ivar(cls, "_" + name) or has_method(cls, "-" + name)
                where = f"self={cls}"
            else:
                ok = name in allivars or "_" + name in allivars or name in allsels
                where = f"recv={recv}"
            if not ok: print(f"  MISSING {os.path.basename(f)}:{n} {where} key={name}")
        for m in re.finditer(r"MSHookIvar<[^>]+>\((\w+),\s*\"(\w+)\"\)", line):
            if m[2] not in allivars: print(f"  MISSING {os.path.basename(f)}:{n} MSHookIvar {m[2]}")
print("=== (b) header-declared YouTube methods missing on class (and its *Impl)")
def strip_types(s):
    p = None
    while p != s: p = s; s = re.sub(r"\([^()]*\)", "", s)
    return s
for h in [f for f in src if f.endswith(".h")]:
    cls = None
    for n, line in enumerate(open(h, encoding="utf-8", errors="ignore"), 1):
        m = re.match(r"@interface\s+(\w+)", line)
        if m: cls = m[1]; continue
        if line.startswith("@end"): cls = None; continue
        if not cls or SYS.match(cls) or not (cls in classes or cls + "Impl" in classes): continue
        s = line.strip()
        if re.match(r"^[-+]\s*\(", s):
            rest = strip_types(s[1:]).split(";")[0]
            parts = re.findall(r"(\w+)\s*:", rest)
            sel = "".join(p + ":" for p in parts) if parts else re.findall(r"\w+", rest)[0]
            if not has_method(cls, s[0] + sel): print(f"  {os.path.basename(h)}:{n} {cls} {s[0]}{sel}")
        elif s.startswith("@property"):
            name = re.findall(r"(\w+)\s*;", s)
            if name and not has_method(cls, "-" + name[-1]) and not has_ivar(cls, "_" + name[-1]):
                print(f"  {os.path.basename(h)}:{n} {cls} property {name[-1]}")
print("=== (c) class lookups by name")
for f in src:
    for n, line in enumerate(open(f, encoding="utf-8", errors="ignore"), 1):
        for m in re.finditer(r"%c\((\w+)\)|objc_getClass\(\"([\w.]+)\"\)|NSClassFromString\(@\"([\w.]+)\"\)", line):
            c = next(g for g in m.groups() if g)
            if not SYS.match(c) and c not in classes and not c.startswith("#"): print(f"  {os.path.basename(f)}:{n} {c}{'  (Impl exists)' if c + 'Impl' in classes else ''}")
