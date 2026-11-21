#!/usr/bin/env python3
"""Editor video Paatik Farm.

Guna:  python3 video/edit.py video/projek/<nama>/skrip.txt
Hasil: video/projek/<nama>/hasil.mp4  (1080x1920, 9:16 untuk TikTok / Reels / WhatsApp Status)

Format skrip.txt (satu baris satu babak, baris bermula # diabaikan):
    HOOK: Ayat besar di atas babak pertama
    klip1.mp4 | 3   | Kapsyen bawah untuk babak ni
    gambar.jpg | 2.5 | Gambar pun boleh, akan zoom perlahan
    MUZIK: lagu.mp3          (pilihan; letak dalam folder projek)
    SUARA_ASAL: ya           (pilihan; kekalkan bunyi asal klip)
    PENUTUP: RM25 sekit | Pos seluruh Malaysia
"""
import os, subprocess, sys, tempfile, textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
F_BOLD = os.path.join(ROOT, "fonts", "Outfit-800.ttf")
F_SEMI = os.path.join(ROOT, "fonts", "Outfit-600.ttf")
W, H, FPS = 1080, 1920, 30
FOREST, KRAFT, CREAM = "0x1f3d2b", "0xd8b98a", "0xeef1ec"
WA, WEB = "WhatsApp 011-1489 2341", "paatikfarm.netlify.app"
IMG = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg gagal:\n" + r.stderr[-2000:])


def txtfile(tmp, text, width):
    p = tempfile.NamedTemporaryFile("w", suffix=".txt", dir=tmp, delete=False, encoding="utf-8")
    p.write("\n".join(textwrap.wrap(text, width)))
    p.close()
    return p.name.replace("\\", "/").replace(":", "\\:")


def draw(tf, font, size, y, color=CREAM, box=None, start=0.0, shadow=False):
    s = (f"drawtext=fontfile='{font}':textfile='{tf}':fontsize={size}:fontcolor={color}"
         f":x=(w-text_w)/2:y={y}:line_spacing=14:text_align=center")
    if shadow:
        s += ":shadowcolor=black@0.55:shadowx=0:shadowy=5"
    if box:
        s += f":box=1:boxcolor={box}:boxborderw=28"
    if start:
        s += f":alpha='if(lt(t,{start}),0,min(1,(t-{start})*4))'"
    return s


def parse(path):
    cfg = {"scenes": [], "hook": "", "music": "", "audio": False, "style": "biasa",
           "end": ["Kit Tanam Cendawan RM25", "Pos seluruh Malaysia"]}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, val = line.partition(":")
        k = key.strip().upper()
        if k == "HOOK" and "|" not in key:
            cfg["hook"] = val.strip()
        elif k == "GAYA":
            cfg["style"] = val.strip().lower()
        elif k == "MUZIK":
            cfg["music"] = val.strip()
        elif k == "SUARA_ASAL":
            cfg["audio"] = val.strip().lower() in ("ya", "yes", "y", "1")
        elif k == "PENUTUP":
            cfg["end"] = [x.strip() for x in val.split("|")]
        else:
            parts = [x.strip() for x in line.split("|")]
            cfg["scenes"].append((parts[0], float(parts[1]) if len(parts) > 1 and parts[1] else 3.0,
                                  parts[2] if len(parts) > 2 else ""))
    return cfg


def scene(src, dur, cap, hook, keep_audio, out, tmp, premium=False):
    fill = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
    is_img = os.path.splitext(src)[1].lower() in IMG
    if is_img:
        frames = int(dur * FPS)
        inp = ["-loop", "1", "-t", str(dur), "-i", src]
        base = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
                f"zoompan=z='min(1+0.0009*on,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={frames}:s={W}x{H}:fps={FPS},setsar=1")
    else:
        inp = ["-t", str(dur), "-i", src]
        base = f"{fill},fps={FPS}"
    vf = [base, "format=yuv420p"]
    if premium:
        vf += ["eq=contrast=1.07:saturation=1.12:gamma=0.96", "vignette=PI/5"]
        if hook:
            vf.append(draw(txtfile(tmp, hook, 18), F_BOLD, 84, "h*0.36", CREAM, None, 0.3, True))
        if cap:
            vf.append(draw(txtfile(tmp, cap, 26), F_SEMI, 52, "h-330", CREAM, None, 0.45, True))
        vf.append(draw(txtfile(tmp, "P A A T I K   F A R M", 60), F_SEMI, 30, 110, KRAFT, None, 0, True))
        vf = [x for x in vf if x]
        return _render(src, inp, vf, dur, keep_audio, is_img, out)
    if hook:
        vf.append(draw(txtfile(tmp, hook, 19), F_BOLD, 88, 240, CREAM, FOREST + "@0.92"))
    if cap:
        vf.append(draw(txtfile(tmp, cap, 22), F_SEMI, 62, "h-440", CREAM, "black@0.55", 0.15))
    vf.append(draw(txtfile(tmp, "PAATIK FARM", 40), F_BOLD, 34, 90, KRAFT))
    return _render(src, inp, vf, dur, keep_audio, is_img, out)


def _render(src, inp, vf, dur, keep_audio, is_img, out):
    has_audio = keep_audio and not is_img and probe_audio(src)
    cmd = ["ffmpeg", "-y", *inp]
    if not has_audio:
        cmd += ["-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-vf", ",".join(vf), "-map", "0:v", "-map", "0:a" if has_audio else "1:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out]
    run(cmd)


def probe_audio(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                        "stream=index", "-of", "csv=p=0", src], capture_output=True, text=True)
    return bool(r.stdout.strip())


def endcard(lines, out, tmp, dur=3.5):
    vf = [draw(txtfile(tmp, "PAATIK FARM", 30), F_BOLD, 60, 380, KRAFT)]
    y = 560
    for i, t in enumerate(lines):
        size = 104 if i == 0 else 60
        vf.append(draw(txtfile(tmp, t, 14 if i == 0 else 26), F_BOLD if i == 0 else F_SEMI, size, y, CREAM, None, 0.2 + i * 0.25))
        y += (size + 14) * len(textwrap.wrap(t, 14 if i == 0 else 26)) + 50
    vf.append(draw(txtfile(tmp, WA, 30), F_BOLD, 58, "h-560", FOREST, KRAFT, 0.8))
    vf.append(draw(txtfile(tmp, WEB, 30), F_SEMI, 50, "h-400", CREAM, None, 1.0))
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={FOREST}:s={W}x{H}:r={FPS}:d={dur}",
         "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=44100:cl=stereo",
         "-vf", ",".join(vf) + ",format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out])


XF = 0.6  # tempoh peralihan lembut (saat) untuk gaya premium


def xfade_join(parts, durs, out):
    cmd = ["ffmpeg", "-y"]
    for p in parts:
        cmd += ["-i", p]
    fc, v, a, off = [], "0:v", "0:a", 0.0
    for i in range(1, len(parts)):
        off += durs[i - 1] - XF
        fc.append(f"[{v}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[v{i}]")
        fc.append(f"[{a}][{i}:a]acrossfade=d={XF}[a{i}]")
        v, a = f"v{i}", f"a{i}"
    cmd += ["-filter_complex", ";".join(fc), "-map", f"[{v}]", "-map", f"[{a}]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
            "-c:a", "aac", out]
    run(cmd)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    skrip = os.path.abspath(sys.argv[1])
    folder = os.path.dirname(skrip)
    cfg = parse(skrip)
    if not cfg["scenes"]:
        sys.exit("Tiada babak dalam skrip.")
    premium = cfg["style"] == "premium"
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, (f, d, cap) in enumerate(cfg["scenes"]):
            src = f if os.path.isabs(f) else os.path.join(folder, f)
            if not os.path.exists(src):
                sys.exit(f"Fail tak jumpa: {src}")
            out = os.path.join(tmp, f"s{i:02d}.mp4")
            print(f"Babak {i+1}: {os.path.basename(src)} ({d}s)")
            scene(src, d, cap, cfg["hook"] if i == 0 else "", cfg["audio"], out, tmp, premium)
            parts.append(out)
        out = os.path.join(tmp, "end.mp4")
        endcard(cfg["end"], out, tmp)
        parts.append(out)
        joined = os.path.join(tmp, "joined.mp4")
        durs = [d for _, d, _ in cfg["scenes"]] + [3.5]
        if premium:
            xfade_join(parts, durs, joined)
            total = sum(durs) - XF * (len(durs) - 1)
        else:
            lst = os.path.join(tmp, "list.txt")
            open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
            run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
            total = sum(durs)
        final = os.path.join(folder, "hasil.mp4")
        if cfg["music"]:
            m = cfg["music"] if os.path.isabs(cfg["music"]) else os.path.join(folder, cfg["music"])
            mix = (f"[1:a]volume=0.35,afade=t=out:st={total-1.5}:d=1.5[m];"
                   f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0,volume=2[a]")
            run(["ffmpeg", "-y", "-i", joined, "-stream_loop", "-1", "-i", m, "-filter_complex", mix,
                 "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest",
                 "-movflags", "+faststart", final])
        else:
            run(["ffmpeg", "-y", "-i", joined, "-c", "copy", "-movflags", "+faststart", final])
    print("Siap:", final)


if __name__ == "__main__":
    main()
