"""Semi-automatic mascot background cutter.

Cartoon mascots sit on flat white. A border flood-fill removes the OUTER white,
but white pockets fully enclosed by the character outline (armpits, gaps between
legs) survive — and so do genuine white FEATURES (eyes, gloves, teeth). They are
geometrically identical, so a human picks which enclosed pockets are background.

analyze(path)          -> writes a labelled PNG + prints component table
apply(path, ids, ...)  -> clears outer bg + chosen enclosed ids, feathers edges,
                          saves the transparent light PNG (and optional dark).
"""
import sys, colorsys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont

WHITE = 236          # strict near-white for region detection
FEATHER_LO = 165     # brightness at/below which a bg-edge pixel stays fully opaque
FEATHER_HI = 246     # brightness at/above which a bg pixel is fully transparent
MIN_AREA = 150       # ignore enclosed specks smaller than this when labelling
TH_ORANGE, _, _ = colorsys.rgb_to_hsv(0xdd/255, 0x91/255, 0x00/255)


def _load(path):
    return np.asarray(Image.open(path).convert('RGBA')).astype(np.int16)


def _regions(arr):
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    white = (r > WHITE) & (g > WHITE) & (b > WHITE)
    lbl, n = ndimage.label(white)                       # 4-conn
    h, w = white.shape
    border_ids = set(lbl[0, :]) | set(lbl[-1, :]) | set(lbl[:, 0]) | set(lbl[:, -1])
    border_ids.discard(0)
    return white, lbl, n, border_ids


def analyze(path, out):
    arr = _load(path)
    white, lbl, n, border_ids = _regions(arr)
    base = arr[..., :3].astype(np.float32)
    vis = base.copy()
    # outer bg -> light magenta tint (keep art visible)
    outer = np.isin(lbl, list(border_ids))
    vis[outer] = 0.4 * vis[outer] + 0.6 * np.array([255, 0, 255])
    rows = []
    disp = 0
    for cid in range(1, n + 1):
        if cid in border_ids:
            continue
        mask = lbl == cid
        area = int(mask.sum())
        if area < MIN_AREA:
            continue
        disp += 1
        ys, xs = np.where(mask)
        cy, cx = int(ys.mean()), int(xs.mean())
        col = np.array([int(c * 255) for c in colorsys.hsv_to_rgb((disp * 0.16) % 1, 1, 1)], float)
        vis[mask] = 0.45 * base[mask] + 0.55 * col
        rows.append((cid, area, cx, cy, xs.min(), xs.max(), ys.min(), ys.max()))
    im = Image.fromarray(vis.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    except Exception:
        font = ImageFont.load_default()
    for cid, area, cx, cy, *_ in rows:
        d.text((cx - 10, cy - 18), str(cid), fill=(0, 0, 0), font=font,
               stroke_width=4, stroke_fill=(255, 255, 255))
    im.save(out)
    print(f"{path}  ({im.width}x{im.height})  enclosed regions >= {MIN_AREA}px:")
    for cid, area, cx, cy, x0, x1, y0, y1 in rows:
        print(f"  id={cid:<4} area={area:<7} center=({cx},{cy})  bbox=({x0},{y0})-({x1},{y1})")


def _feathered_alpha(arr, clear_mask):
    """Within clear_mask, ramp alpha by brightness so white->0, outline->opaque."""
    bright = arr[..., :3].max(axis=2)
    a = arr[..., 3].astype(np.float32)
    ramp = np.clip((FEATHER_HI - bright) / (FEATHER_HI - FEATHER_LO), 0, 1) * 255.0
    a = np.where(clear_mask, np.minimum(a, ramp), a)
    return a.astype(np.uint8)


def _grow_bg(white, lbl, keep_ids, clear_ids, arr):
    """Background = outer + chosen pockets, grown into the antialiased edge."""
    bg = np.isin(lbl, list(clear_ids))
    # include near-white edge pixels touching bg (looser threshold) but never
    # pixels that belong to a KEPT feature region.
    bright = arr[..., :3].max(axis=2)
    edge = (bright > 205)
    grown = ndimage.binary_propagation(bg, mask=(bg | edge))
    keep = np.isin(lbl, list(keep_ids))
    grown &= ~keep
    return grown


def apply(path, clear_extra, out_light, out_dark=None, recolor=True):
    arr = _load(path)
    white, lbl, n, border_ids = _regions(arr)
    clear_ids = set(border_ids) | set(clear_extra)
    keep_ids = set()
    for cid in range(1, n + 1):
        if cid not in clear_ids and (lbl == cid).any():
            keep_ids.add(cid)
    bg = _grow_bg(white, lbl, keep_ids, clear_ids, arr)
    out = arr.copy()
    out[..., 3] = _feathered_alpha(arr, bg)
    Image.fromarray(out.astype(np.uint8)).save(out_light)
    print(f"saved {out_light}  cleared ids={sorted(clear_extra)} (+outer)")
    if out_dark:
        d = out.astype(np.uint8).copy()
        if recolor:
            rgb = d[..., :3].astype(np.float32) / 255.0
            mx = rgb.max(2); mn = rgb.min(2); df = mx - mn
            hue = np.zeros_like(mx)
            mask = df > 1e-6
            r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
            # hue calc
            with np.errstate(invalid='ignore'):
                hr = ((g - b) / df) % 6
                hg = ((b - r) / df) + 2
                hb = ((r - g) / df) + 4
            hue = np.where(mx == r, hr, np.where(mx == g, hg, hb)) * 60
            sat = np.where(mx > 0, df / np.where(mx > 0, mx, 1), 0)
            val = mx
            sel = (hue >= 200) & (hue <= 250) & (sat > 0.35) & (val > 0.20) & (d[..., 3] > 30)
            # recolor selected to orange hue, keep S,V
            i = (TH_ORANGE * 6).astype(int) if False else int(TH_ORANGE * 6)
            f = TH_ORANGE * 6 - i
            vv = val; ss = sat
            p = vv * (1 - ss); q = vv * (1 - ss * f); t = vv * (1 - ss * (1 - f))
            # i == 0 for orange hue (39deg/60 -> 0.65 -> i=0)
            nr, ng, nb = vv, t, p
            d[..., 0] = np.where(sel, (nr * 255), d[..., 0]).astype(np.uint8)
            d[..., 1] = np.where(sel, (ng * 255), d[..., 1]).astype(np.uint8)
            d[..., 2] = np.where(sel, (nb * 255), d[..., 2]).astype(np.uint8)
        Image.fromarray(d).save(out_dark)
        print(f"saved {out_dark}  recolor={recolor}")


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'analyze':
        analyze(sys.argv[2], sys.argv[3])
    elif cmd == 'apply':
        ids = [int(x) for x in sys.argv[3].split(',') if x.strip()] if sys.argv[3] else []
        dark = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
        recolor = (len(sys.argv) > 5 and sys.argv[5] == '1')
        apply(sys.argv[2], ids, sys.argv[3 - 1] if False else sys.argv[3 - 1], dark, recolor)
