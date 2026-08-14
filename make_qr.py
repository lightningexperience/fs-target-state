#!/usr/bin/env python3
"""
make_qr.py — dependency-free QR code generator for the Four Seasons site URL.

Usage:
    python3 make_qr.py "https://your-app-name.herokuapp.com"
    python3 make_qr.py "https://your-app-name.herokuapp.com" --out fs-qr

Writes <out>.svg and (if Pillow is available) <out>.png.
No third-party QR library required — the encoder is built in below.

Encoding used: byte mode, error-correction level M, smallest version that fits.
Good for a URL on a slide, business card, or printed sales asset.
"""
import sys, argparse

# ----------------------------------------------------------------------------
# Minimal QR encoder (byte mode, EC level M). Adapted to be self-contained.
# ----------------------------------------------------------------------------

# Galois field tables for Reed-Solomon
_EXP = [0] * 512
_LOG = [0] * 256
def _init_gf():
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11d
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]
_init_gf()

def _gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]

def _rs_generator(n):
    g = [1]
    for i in range(n):
        g2 = [0] * (len(g) + 1)
        for j in range(len(g)):
            g2[j] ^= _gf_mul(g[j], 1)
            g2[j + 1] ^= _gf_mul(g[j], _EXP[i])
        g = g2
    return g

def _rs_encode(data, n):
    gen = _rs_generator(n)
    res = list(data) + [0] * n
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return res[len(data):]

# Capacity (bytes) in byte mode for EC level M, versions 1..20
_BYTE_CAP_M = {
    1: 14, 2: 26, 3: 42, 4: 62, 5: 84, 6: 106, 7: 122, 8: 152, 9: 180, 10: 213,
    11: 251, 12: 287, 13: 331, 14: 362, 15: 412, 16: 450, 17: 504, 18: 560,
    19: 624, 20: 666,
}
# EC blocks for level M, versions 1..20: (num_blocks, total_codewords, data_codewords) groups
# Format per version: list of (count, data_codewords_per_block)
_EC_M = {
    1: (10, [(1, 16)]), 2: (16, [(1, 28)]), 3: (26, [(1, 44)]), 4: (18, [(2, 32)]),
    5: (24, [(2, 43)]), 6: (16, [(4, 27)]), 7: (18, [(4, 31)]), 8: (22, [(2, 38), (2, 39)]),
    9: (22, [(3, 36), (2, 37)]), 10: (26, [(4, 43), (1, 44)]),
    11: (30, [(1, 50), (4, 51)]), 12: (22, [(6, 36), (2, 37)]),
    13: (22, [(8, 37), (1, 38)]), 14: (24, [(4, 40), (5, 41)]),
    15: (24, [(5, 41), (5, 42)]), 16: (28, [(7, 45), (3, 46)]),
    17: (28, [(10, 46), (1, 47)]), 18: (26, [(9, 43), (4, 44)]),
    19: (26, [(3, 44), (11, 45)]), 20: (26, [(3, 41), (13, 42)]),
}

_ALIGN_POS = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
    7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
    11: [6, 30, 54], 12: [6, 32, 58], 13: [6, 34, 62],
    14: [6, 26, 46, 66], 15: [6, 26, 48, 70], 16: [6, 26, 50, 74],
    17: [6, 30, 54, 78], 18: [6, 30, 56, 82], 19: [6, 30, 58, 86],
    20: [6, 34, 62, 90],
}

def _choose_version(nbytes):
    for v in range(1, 21):
        if nbytes <= _BYTE_CAP_M[v]:
            return v
    raise ValueError("URL too long for this encoder (max version 20). Shorten the URL.")

def _bits_char_count(version):
    return 8 if version < 10 else 16

def _encode_data(data_bytes, version):
    total_data_cw = 0
    for count, dc in _EC_M[version][1]:
        total_data_cw += count * dc
    bits = []
    def put(val, length):
        for i in range(length - 1, -1, -1):
            bits.append((val >> i) & 1)
    put(0b0100, 4)  # byte mode
    put(len(data_bytes), _bits_char_count(version))
    for b in data_bytes:
        put(b, 8)
    # terminator
    cap_bits = total_data_cw * 8
    term = min(4, cap_bits - len(bits))
    put(0, term)
    while len(bits) % 8 != 0:
        bits.append(0)
    # pad bytes
    pad = [0xEC, 0x11]
    i = 0
    while len(bits) < cap_bits:
        put(pad[i % 2], 8)
        i += 1
    # to codewords
    codewords = []
    for i in range(0, len(bits), 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        codewords.append(v)
    return codewords

def _interleave(codewords, version):
    ec_len, groups = _EC_M[version]
    blocks = []
    idx = 0
    for count, dc in groups:
        for _ in range(count):
            data = codewords[idx:idx + dc]
            idx += dc
            ec = _rs_encode(data, ec_len)
            blocks.append((data, ec))
    result = []
    maxd = max(len(d) for d, _ in blocks)
    for i in range(maxd):
        for d, _ in blocks:
            if i < len(d):
                result.append(d[i])
    for i in range(ec_len):
        for _, e in blocks:
            result.append(e[i])
    return result

class _Matrix:
    def __init__(self, size):
        self.size = size
        self.m = [[None] * size for _ in range(size)]
        self.reserved = [[False] * size for _ in range(size)]
    def set(self, r, c, v, reserve=True):
        self.m[r][c] = v
        if reserve:
            self.reserved[r][c] = True

def _place_finder(mat, r, c):
    for dr in range(-1, 8):
        for dc in range(-1, 8):
            rr, cc = r + dr, c + dc
            if 0 <= rr < mat.size and 0 <= cc < mat.size:
                if dr in (0, 6) and 0 <= dc <= 6 or dc in (0, 6) and 0 <= dr <= 6:
                    mat.set(rr, cc, 1)
                elif 2 <= dr <= 4 and 2 <= dc <= 4:
                    mat.set(rr, cc, 1)
                else:
                    mat.set(rr, cc, 0)

def _place_alignment(mat, version):
    pos = _ALIGN_POS[version]
    for r in pos:
        for c in pos:
            # skip if overlapping finders
            if (r <= 8 and c <= 8) or (r <= 8 and c >= mat.size - 9) or (r >= mat.size - 9 and c <= 8):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    rr, cc = r + dr, c + dc
                    if abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0):
                        mat.set(rr, cc, 1)
                    else:
                        mat.set(rr, cc, 0)

def _place_timing(mat):
    for i in range(8, mat.size - 8):
        b = 1 if i % 2 == 0 else 0
        if not mat.reserved[6][i]:
            mat.set(6, i, b)
        if not mat.reserved[i][6]:
            mat.set(i, 6, b)

def _reserve_format(mat):
    for i in range(9):
        if not mat.reserved[8][i]:
            mat.set(8, i, 0)
        if not mat.reserved[i][8]:
            mat.set(i, 8, 0)
    for i in range(8):
        mat.set(8, mat.size - 1 - i, 0)
        mat.set(mat.size - 1 - i, 8, 0)
    mat.set(mat.size - 8, 8, 1)  # dark module

def _place_data(mat, bits):
    size = mat.size
    idx = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rng = range(size - 1, -1, -1) if upward else range(size)
        for row in rng:
            for c in (col, col - 1):
                if not mat.reserved[row][c] and mat.m[row][c] is None:
                    bit = bits[idx] if idx < len(bits) else 0
                    mat.set(row, c, bit, reserve=False)
                    idx += 1
        upward = not upward
        col -= 2

_MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]

def _apply_mask(mat, mask, data_cells):
    fn = _MASKS[mask]
    for (r, c) in data_cells:
        if fn(r, c):
            mat.m[r][c] ^= 1

_FORMAT_EC_M = {  # (mask -> 15-bit format string) for EC level M
    0: 0b101010000010010, 1: 0b101000100100101, 2: 0b101111001111100, 3: 0b101101101001011,
    4: 0b100010111111001, 5: 0b100000011001110, 6: 0b100111110010111, 7: 0b100101010100000,
}

def _place_format(mat, mask):
    fmt = _FORMAT_EC_M[mask]
    bits = [(fmt >> i) & 1 for i in range(14, -1, -1)]
    # top-left
    coords1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
               (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    for i, (r, c) in enumerate(coords1):
        mat.m[r][c] = bits[i]
    size = mat.size
    coords2 = [(size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8),
               (size - 5, 8), (size - 6, 8), (size - 7, 8),
               (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5),
               (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1)]
    for i, (r, c) in enumerate(coords2):
        mat.m[r][c] = bits[i]

def _penalty(mat):
    size = mat.size
    score = 0
    m = mat.m
    # rule 1: runs
    for line in list(m) + [list(col) for col in zip(*m)]:
        run = 1
        for i in range(1, size):
            if line[i] == line[i - 1]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        if run >= 5:
            score += 3 + (run - 5)
    # rule 2: 2x2 blocks
    for r in range(size - 1):
        for c in range(size - 1):
            if m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                score += 3
    # rule 3: finder-like patterns
    pat1 = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    pat2 = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1]
    for line in list(m) + [list(col) for col in zip(*m)]:
        for i in range(size - 10):
            seg = line[i:i + 11]
            if seg == pat1 or seg == pat2:
                score += 40
    # rule 4: dark ratio
    dark = sum(sum(row) for row in m)
    total = size * size
    ratio = dark * 100 // total
    score += min(abs(ratio - 50) // 5, abs((ratio + 4) - 50) // 5) * 10
    return score

def encode(text):
    data = text.encode("utf-8")
    version = _choose_version(len(data))
    codewords = _encode_data(data, version)
    final = _interleave(codewords, version)
    bits = []
    for cw in final:
        for i in range(7, -1, -1):
            bits.append((cw >> i) & 1)
    # remainder bits
    rem = {1:0,2:7,3:7,4:7,5:7,6:7,7:0,8:0,9:0,10:0,11:0,12:0,13:0,
           14:3,15:3,16:3,17:3,18:3,19:3,20:3}[version]
    bits += [0] * rem

    size = version * 4 + 17
    base = _Matrix(size)
    _place_finder(base, 0, 0)
    _place_finder(base, 0, size - 7)
    _place_finder(base, size - 7, 0)
    _place_alignment(base, version)
    _place_timing(base)
    _reserve_format(base)
    _place_data(base, bits)

    # data cells (non-reserved) for masking
    data_cells = [(r, c) for r in range(size) for c in range(size) if not base.reserved[r][c]]

    best = None
    for mask in range(8):
        cand = _Matrix(size)
        cand.m = [row[:] for row in base.m]
        cand.reserved = [row[:] for row in base.reserved]
        _apply_mask(cand, mask, data_cells)
        _place_format(cand, mask)
        p = _penalty(cand)
        if best is None or p < best[0]:
            best = (p, cand)
    return best[1].m

# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------

def to_svg(matrix, scale=10, border=4, dark="#1c2a3a", light="#ffffff"):
    n = len(matrix)
    dim = (n + border * 2) * scale
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{dim}" height="{dim}" '
             f'viewBox="0 0 {dim} {dim}" shape-rendering="crispEdges">']
    parts.append(f'<rect width="{dim}" height="{dim}" fill="{light}"/>')
    for r in range(n):
        for c in range(n):
            if matrix[r][c]:
                x = (c + border) * scale
                y = (r + border) * scale
                parts.append(f'<rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="{dark}"/>')
    parts.append('</svg>')
    return "\n".join(parts)

def to_png(matrix, path, scale=10, border=4, dark=(28, 42, 58), light=(255, 255, 255)):
    try:
        from PIL import Image
    except ImportError:
        return False
    n = len(matrix)
    dim = (n + border * 2) * scale
    img = Image.new("RGB", (dim, dim), light)
    px = img.load()
    for r in range(n):
        for c in range(n):
            if matrix[r][c]:
                x0 = (c + border) * scale
                y0 = (r + border) * scale
                for yy in range(y0, y0 + scale):
                    for xx in range(x0, x0 + scale):
                        px[xx, yy] = dark
    img.save(path)
    return True

def main():
    ap = argparse.ArgumentParser(description="Generate a QR code for a URL (no dependencies).")
    ap.add_argument("url", help="The URL to encode, e.g. https://fs-target-state.herokuapp.com")
    ap.add_argument("--out", default="fs-qr", help="Output base filename (default: fs-qr)")
    ap.add_argument("--scale", type=int, default=12, help="Pixels per module (default: 12)")
    args = ap.parse_args()

    matrix = encode(args.url)
    svg = to_svg(matrix, scale=args.scale)
    with open(args.out + ".svg", "w") as f:
        f.write(svg)
    print(f"Wrote {args.out}.svg  ({len(matrix)}x{len(matrix)} modules)")
    if to_png(matrix, args.out + ".png", scale=args.scale):
        print(f"Wrote {args.out}.png")
    else:
        print("Pillow not installed — SVG only. (pip install Pillow to also get PNG.)")
    print(f"Encodes: {args.url}")

if __name__ == "__main__":
    main()
