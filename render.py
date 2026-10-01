#!/usr/bin/env python3
"""Snowmoon, Chapter 1 - "The Concert": procedural motion-graphics adaptation.
Everything (frames + soundtrack) is generated from code. No AI-generated assets.
Usage: python render.py            -> snowmoon-concert.mp4
       python render.py stills     -> one PNG per scene in ./stills
Needs: Python 3, numpy, scipy, Pillow, ffmpeg.  Source text: https://vitalik.eth.limo/snowmoon/ (GPL v3)
"""
import math, random, sys, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.io import wavfile
from scipy import signal

W, H, FPS, U = 1280, 720, 24, 8          # U = pixels per "unit" (scene is laid out on a 160x90 grid)
SC = [("title", 5), ("concert", 8), ("shout", 6), ("snatch", 9.5), ("chase", 5), ("bus", 6), ("message", 8)]
ST = [sum(d for _, d in SC[:i]) for i in range(len(SC))]
TOTAL = sum(d for _, d in SC)
CAPS = {1: "Gladias, an Acolyte of the Order of Steering, must judge a metal band's social impact. Ten percent chance it costs him his career. He trusts instinct: Tier 3.",
        2: "A stranger shouts. The Order's secrecy game has a bounty on his head.",
        3: "Gladias the philosopher steps aside. The mischievous schoolboy takes over.",
        4: "Throw the device. Run.", 5: "We need more fun in the world."}
D = "/usr/share/fonts/truetype/dejavu/DejaVu"
def font(n, s): return ImageFont.truetype(D + n + ".ttf", s)
FT = font("Serif-Bold", 104); FS = font("Serif", 32); FC = font("Serif", 27); FI = font("Serif-Italic", 24)
FB = font("Sans-Bold", 66); FM = font("SansMono", 21); FSM = font("Sans", 20); FD = font("Sans-Bold", 74)

def lerp(a, b, k):
    k = max(0, min(1, k)); return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
def fade(lt, d, dur=.6): return max(0, min(1, (lt - d) / dur))
def grad(c1, c2):
    a = np.linspace(0, 1, H)[:, None, None]
    return Image.fromarray(((np.array(c1) * (1 - a) + np.array(c2) * a) * np.ones((1, W, 1))).astype("uint8"))
def R(d, x, y, w, h, f, o=None, r=0):
    (d.rounded_rectangle if r else d.rectangle)([x * U, y * U, (x + w) * U, (y + h) * U], fill=f, outline=o, **({"radius": r * U} if r else {}))
def E(d, cx, cy, rx, ry, f, o=None): d.ellipse([(cx - rx) * U, (cy - ry) * U, (cx + rx) * U, (cy + ry) * U], fill=f, outline=o)
def T(d, x, y, s, f, c, a="mm", **k): d.text((x * U, y * U), s, font=f, fill=c, anchor=a, **k)
def robe(d, x, y, s=1, b=0):
    p = [(-5, -2), (-4, -9), (0, -13), (4, -9), (5, -2), (7, 18), (-7, 18)]
    d.polygon([((x + px * s) * U, (y + py * s + b) * U) for px, py in p], fill=(91, 42, 134), outline=(138, 85, 200))
    E(d, x, y - 7 * s + b, 2.6 * s, 3.2 * s, (18, 7, 31)); R(d, x - 3 * s, y - 5.2 * s + b, 6 * s, 1.1 * s, (59, 26, 102))
def bubble(d, x, y, w, h, bg, lines, fnt, fg, k):
    bgc = lerp((0, 0, 0), bg, k); R(d, x, y, w, h, bgc, r=2)
    for i, l in enumerate(lines): T(d, x + w / 2, y + h / 2 + (i - (len(lines) - 1) / 2) * 4.4, l, fnt, lerp((0, 0, 0), fg, k))

BG = [grad((27, 12, 58), (5, 3, 12)), grad((27, 12, 58), (5, 3, 12)), grad((24, 10, 40), (5, 3, 12)), grad((14, 8, 24), (6, 4, 12)),
      grad((10, 6, 20), (6, 3, 12)), grad((23, 16, 42), (14, 10, 28)), grad((27, 12, 58), (5, 3, 12))]
_rs = random.Random(7); d0 = ImageDraw.Draw(BG[0])
for _ in range(90): x, y = _rs.randint(0, W), _rs.randint(0, H); d0.point((x, y), fill=(200, 190, 255))
_v = np.hypot(*np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))); VIG = Image.fromarray((np.clip(_v - .55, 0, 1) * 230).astype("uint8"))
rr = random.Random(3)
CROWD = [(4 + i * 7.4 + (r % 2) * 3, 60 + r * 8, rr.random() * 6, .5 + rr.random() * .6, [(42, 26, 61), (58, 42, 31), (31, 46, 61), (61, 31, 46), (46, 61, 31)][(i + r) % 5], rr.random() < .2) for r in range(3) for i in range(22)]
PH = [(6 + rr.random() * 148, 50 + rr.random() * 28, 1.2 + rr.random() * 2.2) for _ in range(30)]
STK = [(rr.random() * 220, 30 + rr.random() * 50, 20 + rr.random() * 30, 80 + rr.random() * 90) for _ in range(16)]

def crowd(d, lt, sp=1.0):
    for x, y, ph, s, c, fist in CROWD:
        b = math.sin(lt * s * 9 * sp + ph) * .9
        if fist: d.line([((x + 2) * U, (y + 3 + b) * U), ((x + 4) * U, (y - 5 + b) * U)], fill=c, width=9)
        E(d, x, y + b, 2.3, 2.3, c); R(d, x - 2.6, y + 2 + b, 5.2, 7, c, r=1.2)

def title(img, d, lt):
    m = Image.new("L", (W, H), 0); md = ImageDraw.Draw(m)
    md.ellipse([92 * U, 18 * U, 132 * U, 58 * U], fill=int(255 * fade(lt, .2, 1))); md.ellipse([82 * U, 14 * U, 121 * U, 53 * U], fill=0)
    img.paste((232, 228, 255), (0, 0), m); E(d, 132, 22, 4, 4, lerp((5, 3, 12), (205, 187, 255), fade(lt, 1, 1)))
    x = 100
    for ch in "SNOWMOON":
        d.text((x, 270), ch, font=FT, fill=lerp((5, 3, 12), (241, 233, 255), fade(lt, .6 + .08 * x / 100, .8)), anchor="lm"); x += d.textlength(ch, font=FT) + 14
    d.text((104, 370), "CHAPTER 1  ·  THE CONCERT", font=FS, fill=lerp((5, 3, 12), (185, 140, 255), fade(lt, 1.6, .8)), anchor="lm")
    d.text((104, 420), "Meldan, Veridia  ·  3724", font=FSM, fill=lerp((5, 3, 12), (154, 143, 184), fade(lt, 2.4, .8)), anchor="lm")

def concert(img, d, lt):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for k, (c, x) in enumerate([((255, 79, 216), 50), ((79, 210, 255), 80), ((255, 210, 79), 110)]):
        s = 7 * math.sin(lt * 1.3 + k * 2); al = int(65 + 45 * math.sin(lt * (3 + k) + k))
        od.polygon([((x + s * .3) * U, 0), ((x - 10 + s) * U, 60 * U), ((x + 20 + s) * U, 60 * U)], fill=c + (al,))
    img.paste(ov, (0, 0), ov); R(d, 30, 8, 100, 26, (21, 10, 38), (59, 26, 102)); T(d, 80, 21, "DREADKNOT", FD, (255, 59, 92))
    crowd(d, lt); robe(d, 80, 52, 1, math.sin(lt * 2.6) * .5)
    if lt > 3.2:
        k = fade(lt, 3.2, .5); R(d, 112, 62, 34, 19, lerp((0, 0, 0), (15, 42, 34), k), lerp((0, 0, 0), (77, 255, 176), k), r=2)
        T(d, 115, 66, "TIER 3 - neutral", FM, (77, 255, 176), "lm"); R(d, 115, 72, 28, 6, (77, 255, 176) if int(lt * 3) % 2 else (50, 190, 130), r=1); T(d, 129, 75, "SELECT", FM, (5, 20, 15))
    return 1 + .18 * lt / 8, (80 * U, 45 * U)

def shout(img, d, lt):
    R(d, 30, 8, 100, 22, (21, 10, 38)); crowd(d, lt, 2); robe(d, 80, 52)
    for x, y, t0 in PH:
        if lt > t0 and int(lt * 14 + x) % 5: R(d, x - 1, y - 1.6, 2, 3.2, (255, 255, 255))
    if lt > 1.8: robe(d, -20 + 185 * (lt - 1.8) / 3.2, 60, 1, math.sin(lt * 18) * 1.2)
    if lt < 1: img.paste((255, 59, 92), (0, 0), Image.new("L", (W, H), int(190 * (1 - lt))))
    sx, sy = math.sin(lt * 70) * 5, math.cos(lt * 60) * 4
    d.text((W / 2 + sx, 18 * U + sy), "IT'S AN ORDER MEMBER!", font=FB, fill=(255, 59, 92), anchor="mm", stroke_width=4, stroke_fill=(10, 0, 5))

def snatch(img, d, lt):
    E(d, 130, 30, 50, 50, (27, 12, 58))
    E(d, 34, 90, 26, 44, (36, 26, 48)); E(d, 34, 40, 11, 11, (192, 138, 104))
    sh = 3 * fade(lt, 2.6, .5); E(d, 30.5 + sh, 38, 1.1, 1.1, (17, 17, 17)); E(d, 37.5 + sh, 38, 1.1, 1.1, (17, 17, 17))
    E(d, 120, 90, 22, 40, (91, 42, 134), (138, 85, 200)); E(d, 120, 42, 9, 11, (18, 7, 31)); R(d, 111, 43, 18, 2.4, (59, 26, 102))
    p = max(0, min(1, (lt - 3.1) / 1)); p = p * p * (3 - 2 * p); dx = 58 + 52 * p
    if lt < 3.1: d.line([(45 * U, 75 * U), (58 * U, 62 * U)], fill=(36, 26, 48), width=40)
    R(d, dx, 58 + 4 * p, 9, 14, (32, 42, 56), (127, 180, 255), r=1.2); E(d, dx + 4.5, 65 + 4 * p, 2, 2, (127, 180, 255))
    if lt > .5: bubble(d, 8, 6, 52, 12, (241, 233, 255), ["Gotcha, Order boy."], FC, (18, 7, 31), fade(lt, .5, .4))
    if lt > 1.8: bubble(d, 86, 20, 68, 14, (185, 140, 255), ['"Wait - is that a new screed', 'from the Arctic Emperor?"'], FI, (18, 7, 31), fade(lt, 1.8, .4))
    if 4.2 < lt < 6.4:
        R(d, 14, 62, 100, 14, (5, 10, 20), (127, 180, 255)); s1 = "> Delete all audio, images and video"; s2 = "  from the last longhour. Reboot."
        n = int((lt - 4.2) * 28); T(d, 17, 68, s1[:n], FM, (127, 180, 255), "lm"); T(d, 17, 72.6, s2[:max(0, n - len(s1))], FM, (127, 180, 255), "lm")
    if lt >= 6.4: R(d, 14, 62, 100, 14, (5, 10, 20), (255, 59, 92)); T(d, 64, 69, "4 files deleted", FD, (255, 59, 92))
    if lt > 8.3: img.paste((0, 0, 0), (0, 0), Image.new("L", (W, H), int(255 * fade(lt, 8.3, .4))))

def chase(img, d, lt):
    for x, y, w, s in STK: x2 = (x - lt * s) % 240 - 40; d.line([(x2 * U, y * U), ((x2 + w) * U, y * U)], fill=(122, 92, 200), width=3)
    R(d, 0, 74, 160, 16, (18, 10, 32)); robe(d, 70, 56, 1, -abs(math.sin(lt * 11)) * 2.2)
    if .3 < lt < 2.3:
        p = (lt - .3) / 2; cx, cy, a = 62 + 36 * p, 40 - 40 * p + 60 * p * p * .6, p * 9.4
        d.polygon([((cx + (px * math.cos(a) - py * math.sin(a))) * U, (cy + (px * math.sin(a) + py * math.cos(a))) * U) for px, py in [(-2.5, -4), (2.5, -4), (2.5, 4), (-2.5, 4)]], fill=(127, 180, 255))
    if lt > 2.5:
        k = fade(lt, 2.5, .4); R(d, 128, 22, 26, 12, lerp((0, 0, 0), (12, 59, 36), k), lerp((0, 0, 0), (77, 255, 176), k), r=1.5); T(d, 141, 28, "EXIT", FB, lerp((0, 0, 0), (77, 255, 176), k))

def bus(img, d, lt):
    b = math.sin(lt * 14) * .25
    R(d, 8, 10, 144, 30, (10, 24, 48))
    for k in range(5): E(d, (20 + k * 34 - lt * 55) % 170 - 5, 20, 3, 3, (255, 217, 138))
    R(d, 0, 62, 160, 28, (14, 10, 28)); robe(d, 30, 58 + b, 1); robe(d, 46, 58 + b, 1)
    E(d, 128, 48 + b, 4.4, 4.4, (217, 167, 125)); R(d, 122, 52 + b, 12, 16, (58, 120, 200), r=2); R(d, 134, 54 + b, 5, 12, (200, 74, 58), r=1.5)
    robe(d, 84, 58 + b, 1.0)
    if lt > 2: d.arc([82 * U, 49.6 * U, 86 * U, 52 * U], 20, 160, fill=(185, 140, 255), width=3)
    k = fade(lt, 1.5, .5); R(d, 62, 14, 38, 14, lerp((0, 0, 0), (16, 58, 44), k), lerp((0, 0, 0), (232, 224, 74), k))
    T(d, 81, 19, "HYDRAFILL", FM, lerp((0, 0, 0), (232, 224, 74), k)); T(d, 81, 24, "Free of over 2,000 known poisons", font("Sans", 13), lerp((0, 0, 0), (207, 238, 221), k))

def message(img, d, lt):
    R(d, 40, 14, 80, 64, (13, 8, 32), (185, 140, 255), r=5)
    k = fade(lt, .8, .5)
    if k: T(d, 45, 24, "Anonymous  ·  Rep score >= 200  ✓", FSM, lerp((13, 8, 32), (185, 140, 255), k), "lm"); R(d, 44, 28, 72, 12, lerp((13, 8, 32), (36, 20, 70), k), r=2)
    if k: T(d, 47, 32, "I saw you at the concert,", FM, lerp((13, 8, 32), (241, 233, 255), k), "lm"); T(d, 47, 36.6, "I know that you are in the Order.", FM, lerp((13, 8, 32), (241, 233, 255), k), "lm")
    k = fade(lt, 3.2, .5)
    if k:
        R(d, 44, 44, 72, 20, lerp((13, 8, 32), (36, 20, 70), k), r=2)
        for i, l in enumerate(["Don't worry, I'm not intending to", "report you for the bounty. But I do", "have a request that I would like to make."]): T(d, 47, 49 + i * 4.8, l, font("Sans", 17), lerp((13, 8, 32), (241, 233, 255), k), "lm")
    T(d, 80, 84, "Based on Snowmoon by Vitalik Buterin  ·  GPL v3", FSM, lerp((5, 3, 12), (154, 143, 184), fade(lt, 4.4, .8)))

SCN = [title, concert, shout, snatch, chase, bus, message]
def frame(i):
    t = i / FPS; si = max(k for k in range(len(SC)) if t >= ST[k]); lt = t - ST[si]
    img = BG[si].copy(); d = ImageDraw.Draw(img); z = SCN[si](img, d, lt)
    if z and z[0] > 1:
        s, (cx, cy) = z; w, h = W / s, H / s; img = img.crop((int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))).resize((W, H), Image.BILINEAR)
    img.paste((0, 0, 0), (0, 0), VIG); d = ImageDraw.Draw(img); d.rectangle([0, 0, W, 38], fill=(0, 0, 0)); d.rectangle([0, H - 38, W, H], fill=(0, 0, 0))
    if si in CAPS:
        k = fade(lt, .3, .5); words, lines, cur = CAPS[si].split(), [], ""
        for w_ in words:
            if d.textlength(cur + " " + w_, font=FC) > W - 160: lines.append(cur); cur = w_
            else: cur = (cur + " " + w_).strip()
        lines.append(cur)
        for j, l in enumerate(lines):
            y = H - 62 - (len(lines) - 1 - j) * 36; d.text((W / 2 + 2, y + 2), l, font=FC, fill=(0, 0, 0), anchor="mm"); d.text((W / 2, y), l, font=FC, fill=lerp((0, 0, 0), (241, 233, 255), k), anchor="mm")
    f = min(1, t / .6) * min(1, (TOTAL - t) / 1.2)
    return img if f >= 1 else Image.blend(Image.new("RGB", (W, H)), img, max(0, f))

# ---------------- soundtrack (pure numpy synthesis) ----------------
SR = 44100; MIX = np.zeros(int(TOTAL * SR))
def add(sig, w):
    i = int(w * SR); sig = sig[:max(0, len(MIX) - i)]; MIX[i:i + len(sig)] += sig
def tone(f, w, d, ty="sine", v=.2, f2=None, pad=False):
    n = int(d * SR); t = np.arange(n) / SR; fr = f if not f2 else f * (f2 / f) ** (t / d); ph = np.cumsum(fr * np.ones(n)) / SR
    s = {"sine": np.sin(2 * np.pi * ph), "saw": 2 * (ph % 1) - 1, "square": np.sign(np.sin(2 * np.pi * ph)), "tri": 2 * abs(2 * (ph % 1) - 1) - 1}[ty]
    e = np.sin(np.pi * t / d) ** .6 if pad else np.exp(-t * 6.9 / d) * np.minimum(1, t / .01)
    add(s * e * v, w)
def noise(w, d, v, fq, ty="band"):
    n = int(d * SR); x = np.random.RandomState(int(w * 100) % 9999).randn(n)
    sos = signal.butter(2, [fq * .6, min(fq * 1.5, SR / 2 - 100)], "band", fs=SR, output="sos") if ty == "band" else signal.butter(2, fq, "high" if ty == "high" else "low", fs=SR, output="sos")
    add(signal.sosfilt(sos, x) * np.exp(-np.arange(n) / SR * 6.9 / d) * v, w)
RIFF = [41.2, 41.2, 49, 41.2, 55, 41.2, 49, 46.2]
def beat(o, n, bpm, riff=True):
    s = 60 / bpm / 2
    for i in range(n):
        w = o + i * s
        if i % 2 == 0: tone(130, w, .2, v=.9, f2=40)
        if i % 4 == 2: noise(w, .16, 1.2, 2200)
        noise(w, .04, .25, 8000, "high")
        if riff: tone(RIFF[i % 8] * 2, w, s * .9, "saw", .16)
def music():
    o = ST
    tone(110, o[0], 5, pad=True, v=.12); tone(165, o[0], 5, pad=True, v=.08); tone(220, o[0] + .4, 4.4, "tri", .06, pad=True); tone(1320, o[0] + 1.2, 2, v=.05)
    beat(o[1], 16, 120); tone(900, o[1] + 3.2, .08, "square", .1)
    tone(60, o[2], 1.4, "saw", .5, 30); noise(o[2], .6, 1.5, 900); beat(o[2], 4, 150)
    for i in range(8): tone(60, o[2] + 1.9 + i * .7, .25, v=.7, f2=35)
    noise(o[2] + 2, 3, .3, 300)
    tone(82, o[3], 9.4, "saw", .08, pad=True); tone(123, o[3], 9.4, "tri", .05, pad=True)
    for i in range(12): tone(60, o[3] + i * .8, .2, v=.5, f2=35)
    noise(o[3] + 3.1, .5, 1.2, 1500, "low")
    for j in range(14): tone(1800 + (j * 97) % 600, o[3] + 4.2 + j * .12, .04, "square", .05)
    tone(220, o[3] + 6.4, .5, "square", .14); tone(196, o[3] + 6.7, .7, "square", .14)
    beat(o[4], 20, 176); noise(o[4] + .3, .6, 1, 1200); noise(o[4] + 2.4, 1, .5, 3000)
    tone(98, o[5], 6, pad=True, v=.1); tone(147, o[5], 6, "tri", .07, pad=True); noise(o[5], 6, .06, 200, "low")
    for k, f in enumerate([523, 659, 784]): tone(f, o[5] + 2.2 + k * .2, 1.8, v=.05)
    for w in (.8, 3.2): tone(988, o[6] + w, .8, v=.14); tone(1319, o[6] + w + .15, 1.2, v=.12)
    tone(98, o[6], 8, pad=True, v=.08); tone(147, o[6], 8, "tri", .05, pad=True)
    m = np.tanh(MIX * 1.3); m /= np.abs(m).max() / .9
    t = np.arange(len(m)) / SR; m *= np.minimum(1, (TOTAL - t) / 1.5)
    wavfile.write("audio.wav", SR, (m * 32767).astype(np.int16))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        os.makedirs("stills", exist_ok=True)
        for k, (n, dur) in enumerate(SC): frame(int((ST[k] + dur * .6) * FPS)).save(f"stills/{k}_{n}.png")
        sys.exit()
    music(); NF = int(TOTAL * FPS)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", "audio.wav",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest", "snowmoon-concert.mp4"], stdin=subprocess.PIPE)
    for i in range(NF):
        p.stdin.write(frame(i).tobytes())
        if i % 120 == 0: print(i, "/", NF, flush=True)
    p.stdin.close(); p.wait(); print("done")
