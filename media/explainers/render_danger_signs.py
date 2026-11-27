"""Zeya explainer: the nine danger signs in pregnancy (MCH Handbook 2020, p14).

Draws every frame with Pillow at 2x, downsamples, and pipes raw frames to ffmpeg,
one encoded file per scene. Usage:
    python3 render.py stills   # writes a few full-size PNG frames to check
    python3 render.py video    # renders all scenes and joins them
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
S = 2  # supersampling factor
FPS = 30
OUT = os.path.dirname(os.path.abspath(__file__))

INK = (31, 41, 55)
MUTED = (107, 114, 128)
FAINT = (209, 213, 219)
RED = (185, 28, 28)
WHITE = (255, 255, 255)

FONT_DIR = "/usr/share/fonts/opentype/inter"


def font(weight, size):
    return ImageFont.truetype(f"{FONT_DIR}/Inter-{weight}.otf", size * S)


SIGNS = [
    ("headache", "Severe headache", "Maumivu makali ya kichwa"),
    ("pale", "Looking pale", "Kuonekana kupauka"),
    ("bleeding", "Bleeding from the vagina", "Kutokwa na damu ukeni"),
    ("fever", "Fever", "Homa"),
    ("belly", "Severe pain in the belly", "Maumivu makali ya tumbo"),
    ("swelling", "Swelling of the face and hands", "Kuvimba uso na mikono"),
    ("baby", "Baby moving less, or not at all", "Mtoto kucheza kidogo au kutocheza"),
    ("water", "Water breaking", "Maji kutoka (chupa kupasuka)"),
    ("fits", "Convulsions or fits", "Degedege au kifafa"),
]

SOURCE = "Source: Ministry of Health, Mother and Child Health Handbook, page 14"


# ---------- easing and helpers ----------

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def seg(t, start, dur):
    return ease((t - start) / dur)


def mix(c1, c2, a):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * a)) for i in range(3))


def text_w(d, txt, f):
    b = d.textbbox((0, 0), txt, font=f)
    return b[2] - b[0]


def wrap(d, txt, f, maxw):
    words, lines, cur = txt.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if text_w(d, trial, f) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def draw_centered(d, lines, f, y, color, gap=1.18):
    lh = int(f.size * gap)
    for i, ln in enumerate(lines):
        x = (W * S - text_w(d, ln, f)) // 2
        d.text((x, y + i * lh), ln, font=f, fill=color)
    return y + len(lines) * lh


def chrome(d, alpha, index=None):
    """Brand top left, draft label top right, source and progress at the bottom."""
    ink = mix(WHITE, INK, alpha)
    muted = mix(WHITE, MUTED, alpha)
    d.text((48 * S, 52 * S), "Zeya", font=font("SemiBold", 30), fill=ink)
    tag = "Draft for clinical review"
    ft = font("Medium", 18)
    d.text((W * S - 48 * S - text_w(d, tag, ft), 60 * S), tag, font=ft, fill=muted)
    fs = font("Regular", 17)
    lines = wrap(d, SOURCE, fs, (W - 96) * S)
    draw_centered(d, lines, fs, (H - 110) * S, muted, gap=1.35)
    if index is not None:
        n, r, gap = len(SIGNS), 7 * S, 30 * S
        x0 = (W * S - (n - 1) * gap) // 2
        y = (H - 150) * S
        for i in range(n):
            cx = x0 + i * gap
            col = mix(WHITE, RED if i == index else (INK if i < index else FAINT), alpha)
            if i <= index:
                d.ellipse([cx - r, y - r, cx + r, y + r], fill=col)
            else:
                d.ellipse([cx - r, y - r, cx + r, y + r], outline=col, width=2 * S)


# ---------- line icons, drawn in a box centred at (cx, cy) with size u ----------

def icon(d, kind, cx, cy, u, alpha, t=0.0):
    ink = mix(WHITE, INK, alpha)
    red = mix(WHITE, RED, alpha)
    lw = max(2, int(u * 0.045))

    def circle(x, y, r, col, width=lw):
        d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=width)

    if kind == "headache":
        circle(cx, cy + u * 0.12, u * 0.30, ink)
        for k in (-1, 0, 1):
            x = cx + k * u * 0.22
            y = cy - u * 0.30 - (u * 0.06 if k == 0 else 0)
            wob = math.sin(t * 9 + k) * u * 0.015
            pts = [(x - u * 0.05, y + u * 0.06), (x + u * 0.03 + wob, y), (x - u * 0.03 + wob, y - u * 0.07), (x + u * 0.05, y - u * 0.13)]
            d.line(pts, fill=red, width=lw, joint="curve")
    elif kind == "pale":
        pale = mix(WHITE, (156, 163, 175), alpha)
        circle(cx, cy, u * 0.34, pale)
        for sx in (-1, 1):
            ex, ey = cx + sx * u * 0.13, cy - u * 0.05
            d.arc([ex - u * 0.07, ey - u * 0.05, ex + u * 0.07, ey + u * 0.09], 200, 340, fill=ink, width=lw)
            d.arc([ex - u * 0.07, ey - u * 0.02, ex + u * 0.07, ey + u * 0.12], 20, 160, fill=red, width=max(2, lw // 2))
        d.line([(cx - u * 0.10, cy + u * 0.17), (cx + u * 0.10, cy + u * 0.17)], fill=ink, width=lw)
    elif kind == "bleeding":
        top = cy - u * 0.38
        r = u * 0.22
        by = cy + u * 0.10
        d.arc([cx - r, by - r, cx + r, by + r], -20, 200, fill=red, width=lw)
        d.line([(cx - r * math.cos(math.radians(20)), by - r * math.sin(math.radians(20))), (cx, top)], fill=red, width=lw)
        d.line([(cx + r * math.cos(math.radians(20)), by - r * math.sin(math.radians(20))), (cx, top)], fill=red, width=lw)
    elif kind == "fever":
        x0, x1 = cx - u * 0.07, cx + u * 0.07
        d.rounded_rectangle([x0, cy - u * 0.40, x1, cy + u * 0.18], radius=u * 0.07, outline=ink, width=lw)
        circle(cx, cy + u * 0.26, u * 0.13, ink)
        level = cy + u * 0.18 - (u * 0.48) * (0.35 + 0.6 * ease(t / 1.2))
        d.line([(cx, cy + u * 0.24), (cx, level)], fill=red, width=int(lw * 1.6))
        d.ellipse([cx - u * 0.07, cy + u * 0.19, cx + u * 0.07, cy + u * 0.33], fill=red)
        for k in range(3):
            y = cy - u * 0.30 + k * u * 0.12
            d.line([(x1 + u * 0.03, y), (x1 + u * 0.10, y)], fill=ink, width=max(2, lw // 2))
    elif kind == "belly":
        d.arc([cx - u * 0.42, cy - u * 0.30, cx + u * 0.22, cy + u * 0.40], -70, 110, fill=ink, width=lw)
        d.line([(cx - u * 0.30, cy - u * 0.40), (cx - u * 0.30, cy + u * 0.42)], fill=ink, width=lw)
        zx, zy = cx + u * 0.05, cy + u * 0.05
        j = math.sin(t * 12) * u * 0.01
        pts = [(zx - u * 0.16, zy), (zx - u * 0.08, zy - u * 0.08 + j), (zx, zy + j), (zx + u * 0.08, zy - u * 0.08), (zx + u * 0.16, zy)]
        d.line(pts, fill=red, width=lw)
    elif kind == "swelling":
        # a face, with a puffy outline that breathes outwards
        circle(cx, cy, u * 0.26, ink)
        for sx in (-1, 1):
            d.ellipse([cx + sx * u * 0.10 - u * 0.025, cy - u * 0.07, cx + sx * u * 0.10 + u * 0.025, cy - u * 0.02], fill=ink)
        d.line([(cx - u * 0.07, cy + u * 0.09), (cx + u * 0.07, cy + u * 0.09)], fill=ink, width=lw)
        puff = u * (0.36 + 0.025 * math.sin(t * 4))
        for k in range(10):
            a0 = k * 36 + 6
            d.arc([cx - puff, cy - puff, cx + puff, cy + puff], a0, a0 + 22, fill=red, width=lw)
    elif kind == "baby":
        # baby curled inside the womb, with movement marks crossed out
        circle(cx - u * 0.06, cy, u * 0.34, ink)
        circle(cx + u * 0.03, cy - u * 0.12, u * 0.09, ink)
        d.arc([cx - u * 0.24, cy - u * 0.10, cx + u * 0.14, cy + u * 0.24], 90, 300, fill=ink, width=lw)
        mx = cx + u * 0.40
        for k in range(3):
            r = u * (0.06 + k * 0.06)
            d.arc([mx - r, cy - r, mx + r, cy + r], -45, 45, fill=mix(WHITE, (156, 163, 175), alpha), width=max(2, lw // 2))
        d.line([(mx - u * 0.02, cy - u * 0.20), (mx + u * 0.20, cy + u * 0.20)], fill=red, width=lw)
    elif kind == "water":
        for k, (dx, dy, sc) in enumerate([(-0.18, -0.20, 0.7), (0.0, 0.0, 1.0), (0.18, -0.12, 0.6)]):
            fall = (t * 0.6 + k * 0.33) % 1.0
            x, y = cx + dx * u, cy + dy * u + fall * u * 0.25
            r = u * 0.10 * sc
            d.arc([x - r, y - r, x + r, y + r], -20, 200, fill=ink, width=lw)
            d.line([(x - r * 0.94, y - r * 0.34), (x, y - r * 2.4)], fill=ink, width=lw)
            d.line([(x + r * 0.94, y - r * 0.34), (x, y - r * 2.4)], fill=ink, width=lw)
        d.line([(cx - u * 0.40, cy + u * 0.40), (cx + u * 0.40, cy + u * 0.40)], fill=red, width=lw)
    elif kind == "fits":
        j = math.sin(t * 18) * u * 0.012
        pts = [(cx + u * 0.08 + j, cy - u * 0.42), (cx - u * 0.14 + j, cy + u * 0.02), (cx + u * 0.04, cy + u * 0.02), (cx - u * 0.10 - j, cy + u * 0.42)]
        d.line(pts, fill=red, width=int(lw * 1.4), joint="curve")
        for sx in (-1, 1):
            d.arc([cx + sx * u * 0.20 - u * 0.12, cy - u * 0.16, cx + sx * u * 0.20 + u * 0.12, cy + u * 0.16], -60 if sx > 0 else 120, 60 if sx > 0 else 240, fill=ink, width=lw)


# ---------- scenes: each returns a frame function and a duration ----------

def fade_alpha(t, dur, fin=0.35, fout=0.35):
    return min(clamp(t / fin), clamp((dur - t) / fout))


def scene_intro(t, dur):
    img = Image.new("RGB", (W * S, H * S), WHITE)
    d = ImageDraw.Draw(img)
    a = fade_alpha(t, dur)
    chrome(d, a)
    p = seg(t, 0.15, 0.8)
    big = font("Bold", 210)
    num = "9"
    y = int((300 + (1 - p) * 40) * S)
    d.text(((W * S - text_w(d, num, big)) // 2, y), num, font=big, fill=mix(WHITE, RED, a * p))
    p2 = seg(t, 0.5, 0.8)
    ft = font("Bold", 56)
    lines = wrap(d, "danger signs in pregnancy", ft, (W - 120) * S)
    yy = draw_centered(d, lines, ft, int((570 + (1 - p2) * 30) * S), mix(WHITE, INK, a * p2))
    p3 = seg(t, 1.0, 0.8)
    fs = font("Regular", 38)
    lines = wrap(d, "Dalili 9 za hatari wakati wa ujauzito", fs, (W - 140) * S)
    yy = draw_centered(d, lines, fs, yy + 24 * S, mix(WHITE, MUTED, a * p3))
    p4 = seg(t, 1.8, 0.8)
    fx = font("Medium", 30)
    lines = wrap(d, "Know them. Any one means go to a health facility now.", fx, (W - 140) * S)
    draw_centered(d, lines, fx, yy + 70 * S, mix(WHITE, INK, a * p4), gap=1.35)
    return img


def make_sign_scene(i):
    kind, en, sw = SIGNS[i]

    def frame(t, dur):
        img = Image.new("RGB", (W * S, H * S), WHITE)
        d = ImageDraw.Draw(img)
        a = fade_alpha(t, dur)
        chrome(d, a, index=i)
        fn = font("SemiBold", 26)
        lab = f"{i + 1} of 9"
        d.text(((W * S - text_w(d, lab, fn)) // 2, 230 * S), lab, font=fn, fill=mix(WHITE, MUTED, a))
        p = seg(t, 0.1, 0.6)
        u = int(380 * S * (0.88 + 0.12 * p))
        icon(d, kind, W * S // 2, int(520 * S), u, a * p, t)
        p2 = seg(t, 0.45, 0.6)
        fe = font("Bold", 52)
        lines = wrap(d, en, fe, (W - 110) * S)
        y = int((790 + (1 - p2) * 30) * S)
        y = draw_centered(d, lines, fe, y, mix(WHITE, INK, a * p2))
        p3 = seg(t, 0.8, 0.6)
        fsw = font("Regular", 38)
        lines = wrap(d, sw, fsw, (W - 130) * S)
        draw_centered(d, lines, fsw, y + 22 * S, mix(WHITE, MUTED, a * p3))
        return img

    return frame


def scene_recap(t, dur):
    img = Image.new("RGB", (W * S, H * S), WHITE)
    d = ImageDraw.Draw(img)
    a = fade_alpha(t, dur)
    chrome(d, a)
    ft = font("Bold", 44)
    draw_centered(d, ["All nine"], ft, 170 * S, mix(WHITE, INK, a))
    fs = font("Regular", 30)
    draw_centered(d, ["Zote tisa"], fs, 232 * S, mix(WHITE, MUTED, a))
    cell_w, cell_h = 210 * S, 250 * S
    x0 = (W * S - 3 * cell_w) // 2
    y0 = 310 * S
    fl = font("Medium", 20)
    for i, (kind, en, _sw) in enumerate(SIGNS):
        r, c = divmod(i, 3)
        p = seg(t, 0.15 + i * 0.12, 0.5)
        cx = x0 + c * cell_w + cell_w // 2
        cy = y0 + r * cell_h + 85 * S
        icon(d, kind, cx, cy, int(130 * S), a * p, t)
        lines = wrap(d, en, fl, cell_w - 16 * S)
        lh = int(fl.size * 1.2)
        for k, ln in enumerate(lines):
            d.text((cx - text_w(d, ln, fl) // 2, cy + 85 * S + k * lh), ln, font=fl, fill=mix(WHITE, INK, a * p))
    return img


def scene_action(t, dur):
    img = Image.new("RGB", (W * S, H * S), WHITE)
    d = ImageDraw.Draw(img)
    a = fade_alpha(t, dur, fout=0.6)
    chrome(d, a)
    p = seg(t, 0.1, 0.7)
    f1 = font("Bold", 58)
    y = draw_centered(d, wrap(d, "If you see even one sign", f1, (W - 110) * S), f1, int((300 + (1 - p) * 30) * S), mix(WHITE, INK, a * p))
    f2 = font("Regular", 38)
    y = draw_centered(d, wrap(d, "Ukiona dalili moja tu", f2, (W - 130) * S), f2, y + 18 * S, mix(WHITE, MUTED, a * p))
    p2 = seg(t, 0.9, 0.7)
    d.line([(W * S // 2 - 60 * S, y + 60 * S), (W * S // 2 + 60 * S, y + 60 * S)], fill=mix(WHITE, RED, a * p2), width=4 * S)
    f3 = font("Bold", 58)
    y = draw_centered(d, wrap(d, "Go to a health facility now", f3, (W - 110) * S), f3, y + 110 * S, mix(WHITE, RED, a * p2))
    y = draw_centered(d, wrap(d, "Nenda kituo cha afya sasa hivi", f2, (W - 130) * S), f2, y + 18 * S, mix(WHITE, MUTED, a * p2))
    p3 = seg(t, 1.8, 0.7)
    f4 = font("SemiBold", 36)
    y = draw_centered(d, ["Do not wait.", "Usisubiri."], f4, y + 90 * S, mix(WHITE, INK, a * p3), gap=1.4)
    return img


SCENES = [("00_intro", scene_intro, 4.5)]
SCENES += [(f"{i + 1:02d}_{SIGNS[i][0]}", make_sign_scene(i), 3.4) for i in range(len(SIGNS))]
SCENES += [("10_recap", scene_recap, 5.5), ("11_action", scene_action, 6.0)]


def to_frame(img):
    return img.resize((W, H), Image.LANCZOS)


def render_scene(name, fn, dur):
    final = os.path.join(OUT, f"{name}.mp4")
    tmp = os.path.join(OUT, f"{name}.tmp.mp4")
    n = int(round(dur * FPS))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", str(FPS), tmp,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        proc.stdin.write(to_frame(fn(k / FPS, dur)).tobytes())
    proc.stdin.close()
    if proc.wait() == 0:
        os.replace(tmp, final)
    else:
        raise SystemExit(f"ffmpeg failed on {name}")
    return final


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "stills"
    if mode == "stills":
        picks = [(SCENES[0], 3.0), (SCENES[3], 2.0), (SCENES[6], 2.0), (SCENES[7], 2.0), (SCENES[10], 3.5), (SCENES[11], 4.0)]
        for (name, fn, dur), t in picks:
            to_frame(fn(t, dur)).save(os.path.join(OUT, f"still_{name}.png"))
        print("stills done")
    else:
        files = [render_scene(*s) for s in SCENES]
        lst = os.path.join(OUT, "list.txt")
        with open(lst, "w") as fh:
            for f in files:
                fh.write(f"file '{f}'\n")
        out = os.path.join(OUT, "zeya_danger_signs_draft.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                        "-c", "copy", "-movflags", "+faststart", out], check=True)
        print("video done", out)


if __name__ == "__main__":
    main()
