#!/usr/bin/env python3
"""
asc2contour.py - Convert OS Terrain 50 ASCII Grid (.asc) to CONTOUR.DAT
By Kayto 20/03/2026
Licensed under the MIT License. See LICENSE file for details.
Reads OS Terrain 50 .asc files (or .zip archives containing them),
traces contour lines using marching squares, and outputs CONTOUR.DAT
format for the Husky Hunter TERRAIN.HBA terrain profiler.

Usage:
    python asc2contour.py TQ00.asc
    python asc2contour.py TQ00.asc TQ01.asc TQ10.asc TQ11.asc
    python asc2contour.py tiles/tq27.zip tiles/tq28.zip -i 20
    python asc2contour.py path/to/extracted_folder/

Output format (CONTOUR.DAT):
    A,origin_e,origin_n,width,height    (hectometres)
    C,level,num_vertices                (metres ASL, integer)
    easting,northing                    (hectometres, offset from origin)
    ...

OS Terrain 50 data: https://osdatahub.os.uk/downloads/open/Terrain50
"""

import argparse
import glob
import math
import os
import struct
import sys
import tempfile
import zipfile
from collections import defaultdict


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def find_asc_files(paths):
    """Resolve input paths to .asc file paths.

    Handles: .asc files, .zip files (auto-extract), directories
    (scans for .asc in dir and immediate subdirs).
    """
    result = []
    # Expand globs (Windows doesn't expand them)
    expanded = []
    for path in paths:
        matches = glob.glob(path)
        expanded.extend(matches if matches else [path])

    for path in expanded:
        if os.path.isdir(path):
            # Look for .asc files in dir and immediate subdirs
            for entry in sorted(os.listdir(path)):
                fp = os.path.join(path, entry)
                if entry.lower().endswith('.asc'):
                    result.append(fp)
                elif os.path.isdir(fp):
                    for f in sorted(os.listdir(fp)):
                        if f.lower().endswith('.asc'):
                            result.append(os.path.join(fp, f))
        elif path.lower().endswith('.zip'):
            result.extend(extract_asc_from_zip(path))
        elif path.lower().endswith('.asc'):
            result.append(path)
    return result


def extract_asc_from_zip(zippath):
    """Extract .asc file(s) from a zip archive, return list of paths."""
    extracted = []
    outdir = os.path.join(tempfile.gettempdir(), 'asc2contour')
    os.makedirs(outdir, exist_ok=True)
    with zipfile.ZipFile(zippath, 'r') as zf:
        for name in zf.namelist():
            if name.lower().endswith('.asc'):
                zf.extract(name, outdir)
                extracted.append(os.path.join(outdir, name))
    return extracted


# ---------------------------------------------------------------------------
# ASCII Grid reader
# ---------------------------------------------------------------------------

def read_asc(filepath):
    """Read ESRI ASCII Grid file.

    Returns (header_dict, 2D_list_of_floats).
    Header keys: ncols, nrows, xllcorner, yllcorner, cellsize, nodata_value.
    Data: row 0 = northernmost (top), values left to right.
    """
    header = {}
    with open(filepath, 'r') as f:
        # Read header key-value pairs
        while True:
            pos = f.tell()
            line = f.readline()
            if not line:
                break
            parts = line.split()
            if len(parts) >= 2 and parts[0][0].isalpha():
                header[parts[0].lower()] = float(parts[1])
            else:
                f.seek(pos)
                break

        if 'nodata_value' not in header:
            header['nodata_value'] = -9999.0

        ncols = int(header['ncols'])
        nrows = int(header['nrows'])
        data = []
        for _ in range(nrows):
            row = []
            while len(row) < ncols:
                line = f.readline()
                if not line:
                    break
                row.extend(float(v) for v in line.split())
            data.append(row[:ncols])
    return header, data


# ---------------------------------------------------------------------------
# Grid merging
# ---------------------------------------------------------------------------

def merge_grids(grids):
    """Merge multiple (header, data) tiles into a single grid."""
    if len(grids) == 1:
        return grids[0]

    cs = grids[0][0]['cellsize']
    nodata = grids[0][0].get('nodata_value', -9999.0)

    min_x = min(h['xllcorner'] for h, _ in grids)
    min_y = min(h['yllcorner'] for h, _ in grids)
    max_x = max(h['xllcorner'] + int(h['ncols']) * cs for h, _ in grids)
    max_y = max(h['yllcorner'] + int(h['nrows']) * cs for h, _ in grids)

    total_cols = int(round((max_x - min_x) / cs))
    total_rows = int(round((max_y - min_y) / cs))

    # Initialise with NODATA
    merged = [[nodata] * total_cols for _ in range(total_rows)]

    for header, data in grids:
        col_off = int(round((header['xllcorner'] - min_x) / cs))
        row_off = int(round((max_y - header['yllcorner']
                             - int(header['nrows']) * cs) / cs))
        nr = int(header['nrows'])
        nc = int(header['ncols'])
        for r in range(nr):
            mr = row_off + r
            if 0 <= mr < total_rows:
                for c in range(nc):
                    mc = col_off + c
                    if 0 <= mc < total_cols:
                        merged[mr][mc] = data[r][c]

    merged_header = {
        'ncols': total_cols, 'nrows': total_rows,
        'xllcorner': min_x, 'yllcorner': min_y,
        'cellsize': cs, 'nodata_value': nodata
    }
    return merged_header, merged


# ---------------------------------------------------------------------------
# Marching squares contour tracer
# ---------------------------------------------------------------------------

def marching_squares(header, data, level):
    """Trace contour at given level using marching squares.

    Returns list of line segments as ((x1,y1), (x2,y2)) in OS Grid metres.
    """
    nrows = int(header['nrows'])
    ncols = int(header['ncols'])
    xll = header['xllcorner']
    yll = header['yllcorner']
    cs = header['cellsize']
    nodata = header.get('nodata_value', -9999.0)

    segments = []

    for r in range(nrows - 1):
        # Y coordinates for this row of cells (north at top)
        y0 = yll + (nrows - 1 - r) * cs       # top edge
        y1 = y0 - cs                           # bottom edge

        for c in range(ncols - 1):
            tl = data[r][c]
            tr = data[r][c + 1]
            bl = data[r + 1][c]
            br = data[r + 1][c + 1]

            # Skip cells touching NODATA
            if tl == nodata or tr == nodata or bl == nodata or br == nodata:
                continue

            # Classify corners: bit3=TL bit2=TR bit1=BR bit0=BL
            code = 0
            if tl >= level: code |= 8
            if tr >= level: code |= 4
            if br >= level: code |= 2
            if bl >= level: code |= 1

            if code == 0 or code == 15:
                continue

            # Cell X coordinates
            x0 = xll + c * cs
            x1c = x0 + cs   # renamed to avoid shadowing y1

            # Edge intersection points (linear interpolation)
            # Top edge: TL → TR
            dt = tr - tl
            tt = (level - tl) / dt if abs(dt) > 1e-10 else 0.5
            T = (x0 + tt * cs, y0)

            # Right edge: TR → BR
            dr = br - tr
            rt = (level - tr) / dr if abs(dr) > 1e-10 else 0.5
            R = (x1c, y0 - rt * cs)

            # Bottom edge: BL → BR
            db = br - bl
            bt = (level - bl) / db if abs(db) > 1e-10 else 0.5
            B = (x0 + bt * cs, y1)

            # Left edge: TL → BL
            dl = bl - tl
            lt = (level - tl) / dl if abs(dl) > 1e-10 else 0.5
            L = (x0, y0 - lt * cs)

            # Generate segments by case
            if code in (1, 14):
                segments.append((L, B))
            elif code in (2, 13):
                segments.append((B, R))
            elif code in (3, 12):
                segments.append((L, R))
            elif code in (4, 11):
                segments.append((T, R))
            elif code == 5:     # Saddle: BL & TR above
                avg = (tl + tr + bl + br) * 0.25
                if avg >= level:
                    segments.append((T, L))
                    segments.append((B, R))
                else:
                    segments.append((T, R))
                    segments.append((L, B))
            elif code in (6, 9):
                segments.append((T, B))
            elif code in (7, 8):
                segments.append((T, L))
            elif code == 10:    # Saddle: TL & BR above
                avg = (tl + tr + bl + br) * 0.25
                if avg >= level:
                    segments.append((T, R))
                    segments.append((L, B))
                else:
                    segments.append((T, L))
                    segments.append((B, R))

    return segments


# ---------------------------------------------------------------------------
# Segment chaining
# ---------------------------------------------------------------------------

def chain_segments(segments):
    """Chain individual line segments into polylines.

    Adjacent cells share edges, so their segment endpoints match exactly.
    Returns list of polylines (each a list of (x,y) tuples).
    """
    if not segments:
        return []

    # Round to 0.1m to handle any floating-point drift
    def key(pt):
        return (round(pt[0], 1), round(pt[1], 1))

    # Adjacency: endpoint → [(segment_index, other_endpoint_key, other_point)]
    adj = defaultdict(list)
    for i, (p1, p2) in enumerate(segments):
        adj[key(p1)].append((i, key(p2), p2))
        adj[key(p2)].append((i, key(p1), p1))

    used = set()
    polylines = []

    for i, (p1, p2) in enumerate(segments):
        if i in used:
            continue
        used.add(i)
        chain = [p1, p2]

        # Extend forward from p2
        cur = key(p2)
        while True:
            found = False
            for si, ok, opt in adj[cur]:
                if si not in used:
                    used.add(si)
                    chain.append(opt)
                    cur = ok
                    found = True
                    break
            if not found:
                break

        # Extend backward from p1
        cur = key(p1)
        while True:
            found = False
            for si, ok, opt in adj[cur]:
                if si not in used:
                    used.add(si)
                    chain.insert(0, opt)
                    cur = ok
                    found = True
                    break
            if not found:
                break

        polylines.append(chain)

    return polylines


# ---------------------------------------------------------------------------
# Douglas-Peucker simplification (iterative)
# ---------------------------------------------------------------------------

def simplify(points, tolerance):
    """Reduce polyline vertices. Tolerance in metres."""
    n = len(points)
    if n <= 2:
        return points

    keep = [False] * n
    keep[0] = True
    keep[n - 1] = True

    stack = [(0, n - 1)]
    while stack:
        start, end = stack.pop()
        if end - start <= 1:
            continue

        sx, sy = points[start]
        ex, ey = points[end]
        dx, dy = ex - sx, ey - sy
        line_len = math.sqrt(dx * dx + dy * dy)

        max_dist = 0.0
        max_idx = start
        for i in range(start + 1, end):
            px, py = points[i]
            if line_len < 1e-10:
                d = math.sqrt((px - sx) ** 2 + (py - sy) ** 2)
            else:
                d = abs(dx * (sy - py) - dy * (sx - px)) / line_len
            if d > max_dist:
                max_dist = d
                max_idx = i

        if max_dist > tolerance:
            keep[max_idx] = True
            stack.append((start, max_idx))
            stack.append((max_idx, end))

    return [p for p, k in zip(points, keep) if k]


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def write_contour_dat(filename, origin_e, origin_n, width, height,
                      contours, min_verts):
    """Write CONTOUR.DAT format with delta-encoded vertices.

    contours: list of (level, [(x_metres, y_metres), ...])
    Coordinates converted to integer hectometres offset from origin.
    First vertex of each segment is absolute, subsequent are deltas.
    """
    total_segs = 0
    total_verts = 0

    with open(filename, 'w', newline='\r\n') as f:
        f.write('"A",%d,%d,%d,%d\n' % (origin_e, origin_n, width, height))

        for level, pts in contours:
            # Convert metres → hectometres offset from origin
            hm_pts = []
            for x, y in pts:
                he = int(round(x / 100.0 - origin_e))
                hn = int(round(y / 100.0 - origin_n))
                # Remove consecutive duplicates (from rounding)
                if not hm_pts or (he, hn) != hm_pts[-1]:
                    hm_pts.append((he, hn))

            if len(hm_pts) < min_verts:
                continue

            f.write('"C",%d,%d\n' % (int(level), len(hm_pts)))
            # First vertex: absolute
            f.write('%d,%d\n' % (hm_pts[0][0], hm_pts[0][1]))
            # Subsequent vertices: delta from previous
            for j in range(1, len(hm_pts)):
                de = hm_pts[j][0] - hm_pts[j-1][0]
                dn = hm_pts[j][1] - hm_pts[j-1][1]
                f.write('%d,%d\n' % (de, dn))
            total_segs += 1
            total_verts += len(hm_pts)

    # Strip trailing newline to prevent EOF misdetection on Hunter
    with open(filename, 'rb') as f:
        data = f.read()
    with open(filename, 'wb') as f:
        f.write(data.rstrip(b'\r\n'))

    return total_segs, total_verts


def write_contour_bin(filename, origin_e, origin_n, width, height,
                      contours, min_verts):
    """Write binary contour format for MBASIC random file I/O.

    Format: stream of little-endian int16 values in 128-byte records.
    Header: 0, origin_e, origin_n, width, height
    Per segment: level, vertex_count, e1, n1, de2, dn2, ...
    End marker: -32768
    Last record padded to 128 bytes.
    """
    total_segs = 0
    total_verts = 0
    buf = bytearray()

    def put_int16(v):
        buf.extend(struct.pack('<h', int(v)))

    # Area header
    put_int16(0)         # marker (distinguishes from ASCII 'A')
    put_int16(origin_e)
    put_int16(origin_n)
    put_int16(width)
    put_int16(height)

    for level, pts in contours:
        # Convert metres -> hectometres offset from origin
        hm_pts = []
        for x, y in pts:
            he = int(round(x / 100.0 - origin_e))
            hn = int(round(y / 100.0 - origin_n))
            if not hm_pts or (he, hn) != hm_pts[-1]:
                hm_pts.append((he, hn))

        if len(hm_pts) < min_verts:
            continue

        put_int16(int(level))
        put_int16(len(hm_pts))
        # First vertex: absolute
        put_int16(hm_pts[0][0])
        put_int16(hm_pts[0][1])
        # Subsequent vertices: delta from previous
        for j in range(1, len(hm_pts)):
            de = hm_pts[j][0] - hm_pts[j - 1][0]
            dn = hm_pts[j][1] - hm_pts[j - 1][1]
            put_int16(de)
            put_int16(dn)
        total_segs += 1
        total_verts += len(hm_pts)

    # End marker
    put_int16(-32768)

    # Pad to 128-byte record boundary
    remainder = len(buf) % 128
    if remainder:
        buf.extend(bytes(128 - remainder))

    with open(filename, 'wb') as f:
        f.write(buf)

    return total_segs, total_verts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Convert OS Terrain 50 ASCII Grid to CONTOUR.DAT',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python asc2contour.py TQ00.asc
  python asc2contour.py TQ00.asc TQ01.asc TQ10.asc TQ11.asc
  python asc2contour.py tiles/tq27.zip tiles/tq28.zip -i 20
  python asc2contour.py path/to/extracted/ -o KENT.DAT""")

    parser.add_argument('inputs', nargs='+',
                        help='.asc files, .zip files, or directories')
    parser.add_argument('-i', '--interval', type=int, default=10,
                        help='contour interval in metres (default: 10)')
    parser.add_argument('-o', '--output', default='CONTOUR.DAT',
                        help='output filename (default: CONTOUR.DAT)')
    parser.add_argument('-s', '--simplify', type=float, default=50.0,
                        help='simplification tolerance in metres (default: 50)')
    parser.add_argument('-m', '--min-vertices', type=int, default=2,
                        help='min vertices per contour segment (default: 2)')
    parser.add_argument('-b', '--binary', action='store_true',
                        help='write binary format (.BIN) for MBASIC random file I/O')
    args = parser.parse_args()

    # Auto-change default output for binary mode
    if args.binary and args.output == 'CONTOUR.DAT':
        args.output = 'CONTOUR.BIN'

    # --- Discover .asc files ---
    asc_files = find_asc_files(args.inputs)
    if not asc_files:
        print('No .asc files found in the given paths.')
        print('Pass .asc files, .zip archives, or directories containing them.')
        sys.exit(1)

    print('Found %d tile(s):' % len(asc_files))
    for f in asc_files:
        print('  %s' % os.path.basename(f))

    # --- Read tiles ---
    grids = []
    for f in asc_files:
        print('Reading %s...' % os.path.basename(f))
        grids.append(read_asc(f))

    # --- Merge ---
    if len(grids) > 1:
        print('Merging %d tiles...' % len(grids))
    header, data = merge_grids(grids)

    ncols = int(header['ncols'])
    nrows = int(header['nrows'])
    xll = header['xllcorner']
    yll = header['yllcorner']
    cs = header['cellsize']
    nodata = header.get('nodata_value', -9999.0)

    # Area bounds in hectometres
    origin_e = int(xll / 100)
    origin_n = int(yll / 100)
    width = int(ncols * cs / 100)
    height = int(nrows * cs / 100)

    print('Area: origin %d,%d  size %dx%d hm (%dx%d km)' %
          (origin_e, origin_n, width, height, width // 10, height // 10))
    print('Grid: %d x %d cells, %.0fm spacing' % (ncols, nrows, cs))

    # --- Elevation range (excluding NODATA) ---
    min_h = float('inf')
    max_h = float('-inf')
    for row in data:
        for v in row:
            if v != nodata:
                if v < min_h:
                    min_h = v
                if v > max_h:
                    max_h = v

    if min_h == float('inf'):
        print('No valid elevation data found.')
        sys.exit(1)

    print('Elevation: %.1f to %.1f m' % (min_h, max_h))

    # --- Determine contour levels ---
    first_level = int(math.ceil(min_h / args.interval)) * args.interval
    last_level = int(math.floor(max_h / args.interval)) * args.interval
    levels = list(range(first_level, last_level + 1, args.interval))
    if not levels:
        print('No contour levels in elevation range.')
        sys.exit(1)

    print('Tracing %d levels (%dm to %dm, interval %dm)...' %
          (len(levels), first_level, last_level, args.interval))

    # --- Trace contours ---
    all_contours = []
    for li, level in enumerate(levels):
        sys.stdout.write('\r  Level %dm (%d/%d)' %
                         (level, li + 1, len(levels)))
        sys.stdout.flush()

        segments = marching_squares(header, data, level)
        if not segments:
            continue

        polylines = chain_segments(segments)
        for pts in polylines:
            if args.simplify > 0:
                pts = simplify(pts, args.simplify)
            all_contours.append((level, pts))

    print('\r  %d contour segments traced.        ' % len(all_contours))

    # --- Write output ---
    writer = write_contour_bin if args.binary else write_contour_dat
    total_segs, total_verts = writer(
        args.output, origin_e, origin_n, width, height,
        all_contours, args.min_vertices)

    fsize = os.path.getsize(args.output)
    fmt = 'binary' if args.binary else 'ASCII'
    print()
    print('Written: %s (%s)' % (args.output, fmt))
    print('  %d segments, %d vertices' % (total_segs, total_verts))
    print('  File size: %d bytes (%.1f KB)' % (fsize, fsize / 1024))

    if fsize > 129000:
        print()
        print('  WARNING: File exceeds ~129KB Hunter storage limit.')
        print('  Try: larger interval (-i 20), more simplification (-s 100),')
        print('       or fewer input tiles.')


if __name__ == '__main__':
    main()
