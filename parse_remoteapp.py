# Parse binary AXML key/value entries from remoteapp.xml
import struct

data = open('apk_raw/res/xml/remoteapp.xml', 'rb').read()
N = len(data)

def rd(fmt, off):
    return struct.unpack_from(fmt, data, off)

# string pool at offset 8
ctype, hdrsz, size = rd('<HHI', 8)
strcount, stylecount, flags, strstart, stylestart = rd('<IIIII', 8 + 8)
utf8 = bool(flags & (1 << 8))
strs_off = 8 + strstart
sp = []
for i in range(strcount):
    offs = rd('<I', 8 + hdrsz + i * 4)[0]
    p = strs_off + offs
    if p >= N:
        sp.append('')
        continue
    if utf8:
        u16len = rd('<H', p)[0]; p += 2
        if u16len & 0x8000:
            u16len = ((u16len & 0x7fff) << 16) | rd('<H', p)[0]; p += 2
        if p >= N:
            sp.append(''); continue
        blen = data[p]; p += 1
        if blen & 0x80:
            blen = ((blen & 0x7f) << 8) | data[p]; p += 1
        s = data[p:p + blen].decode('utf-8', 'ignore')
    else:
        l = rd('<H', p)[0]; p += 2
        s = data[p:p + l * 2].decode('utf-16-le', 'ignore')
    sp.append(s)

def name_of(idx):
    return sp[idx] if 0 <= idx < len(sp) else f'#{idx}'

entries = {}
stack = []  # (tagname, attr_value)
o = 8 + size  # skip string pool; 0x0180 resource map (8 bytes) follows
o += 8
while o + 8 <= N:
    ctype, hdrsz, csize = rd('<HHI', o)
    if csize < 8 or o + csize > N:
        break
    if ctype == 0x0104 and csize >= 28 and o + csize <= N:  # TEXT
        _, ext_name = rd('<iI', o + 20)
        txt = name_of(ext_name)
        if stack:
            stack[-1] = (stack[-1][0], txt)
    elif ctype == 0x0103 and o + 24 <= N:  # END_ELEMENT
        _, ext_name = rd('<iI', o + 20)
        name = name_of(ext_name)
        if stack:
            sname, sattr = stack.pop()
            if sname in ('key', 'value'):
                stack.append(('_' + sname, sattr))
            elif sname == 'entry':
                k = v = None
                for nm, av in stack:
                    if nm == '_key': k = av
                    if nm == '_value': v = av
                stack = [x for x in stack if not x[0].startswith('_')]
                if k is not None:
                    entries[k] = v
    o += csize

print("TOTAL ENTRIES:", len(entries))
for k, v in entries.items():
    print(f'{k} = {v}')
