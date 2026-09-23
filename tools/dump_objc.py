# Dump ObjC classes/methods/ivars from a decrypted YouTube IPA: python tools/dump_objc.py YouTube.ipa out.txt
# Dump ObjC classes/categories (methods with type encodings, ivars) from a YouTube IPA's main binary.
import zipfile, struct, sys
ipa, out = sys.argv[1], sys.argv[2]
d = zipfile.ZipFile(ipa).read("Payload/YouTube.app/YouTube")
ncmds = struct.unpack_from("<I", d, 16)[0]; p = 32; secs = {}; segs = []
for _ in range(ncmds):
    cmd, size = struct.unpack_from("<II", d, p)
    if cmd == 0x19:
        vmaddr, vmsize, fileoff = struct.unpack_from("<QQQ", d, p + 24)
        segs.append((vmaddr, vmsize, fileoff))
        for i in range(struct.unpack_from("<I", d, p + 64)[0]):
            s = p + 72 + i * 80
            name = d[s:s+16].rstrip(b"\0").decode()
            addr, sz, off = struct.unpack_from("<QQI", d, s + 32); secs[name] = (addr, sz, off)
    p += size
BASE = 0x100000000
def a2o(a):
    for vm, sz, fo in segs:
        if vm <= a < vm + sz: return fo + (a - vm)
    return None
def ptr(a):
    o = a2o(a)
    if o is None: return 0
    v = struct.unpack_from("<Q", d, o)[0]
    if v >> 63: return 0  # bind (external symbol)
    t = v & 0xFFFFFFFFF
    return t + BASE if t < BASE else t
def cstr(a):
    o = a2o(a)
    if o is None: return "?"
    return d[o:d.index(b"\0", o)].decode("utf-8", "replace")
def methods(ml):
    if not ml: return []
    o = a2o(ml)
    if o is None: return []
    es, cnt = struct.unpack_from("<II", d, o); res = []
    if cnt > 20000: return []
    if es & 0x80000000:
        for i in range(cnt):
            e = ml + 8 + i * 12; eo = o + 8 + i * 12
            n, t = struct.unpack_from("<ii", d, eo)
            res.append((cstr(ptr(e + n)), cstr(e + 4 + t)))
    else:
        for i in range(cnt):
            e = ml + 8 + i * (es & 0xFFFC)
            res.append((cstr(ptr(e)), cstr(ptr(e + 8))))
    return res
def ivars(il):
    if not il: return []
    o = a2o(il)
    if o is None: return []
    es, cnt = struct.unpack_from("<II", d, o)
    if cnt > 20000 or es < 24: return []
    return [(cstr(ptr(il + 8 + i * es + 8)), cstr(ptr(il + 8 + i * es + 16))) for i in range(cnt)]
def ro(cls):
    return ptr(cls + 32) & ~7
lines = []
def dump_class(cls):
    r = ro(cls)
    if not r: return
    name = cstr(ptr(r + 24)); sup = ptr(cls + 8)
    supname = cstr(ptr(ro(sup) + 24)) if sup and ro(sup) else "?"
    lines.append(f"@class {name} : {supname}")
    for s, t in methods(ptr(r + 32)): lines.append(f"{name} -{s} {t}")
    meta = ptr(cls)
    if meta and ro(meta):
        for s, t in methods(ptr(ro(meta) + 32)): lines.append(f"{name} +{s} {t}")
    for n, t in ivars(ptr(r + 48)): lines.append(f"{name} ivar {n} {t}")
a, sz, o = secs["__objc_classlist"]
for i in range(0, sz, 8): dump_class(ptr(a + i))
for sec in ("__objc_catlist", "__objc_catlist2"):
    if sec not in secs: continue
    a, sz, o = secs[sec]
    for i in range(0, sz, 8):
        c = ptr(a + i); cname = cstr(ptr(c)); cls = ptr(c + 8)
        target = cstr(ptr(ro(cls) + 24)) if cls and ro(cls) else "?ext"
        for s, t in methods(ptr(c + 16)): lines.append(f"{target}({cname}) -{s} {t}")
        for s, t in methods(ptr(c + 24)): lines.append(f"{target}({cname}) +{s} {t}")
open(out, "w", encoding="utf-8").write("\n".join(lines))
print(len(lines), "lines;", sum(l.startswith("@class") for l in lines), "classes")
