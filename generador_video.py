#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generador_video.py
Genera un documental largo (clips/fotos reales de Pexels/Pixabay/Wikimedia +
voz de ElevenLabs + montaje FFmpeg) y lo sube a YouTube como PRIVADO para
revisarlo a mano. Pensado para correr en GitHub Actions (sin Colab, sin navegador).

Config por variables de entorno (Secrets del repo). Ver requirements-video.txt.
"""
import os, sys, json, subprocess, shutil, re, datetime, urllib.request
import requests

# ----------------------------- CONFIG (env / Secrets) -----------------------------
def env(name, default=None):
    v = os.environ.get(name)
    return v if (v is not None and v != "") else default

def flag(name, default="0"):
    return env(name, default).strip().lower() in ("1", "true", "yes", "si", "sí")

PEXELS_API_KEY     = env("PEXELS_API_KEY")
PIXABAY_API_KEY    = env("PIXABAY_API_KEY")
ELEVENLABS_API_KEY = env("ELEVENLABS_API_KEY")

GOOGLE_CLIENT_ID      = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET  = env("GOOGLE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = env("YOUTUBE_REFRESH_TOKEN")

VOICE_ID      = env("VOICE_ID", "o0SveC0zgHFuCsEO3vHR")   # David Martín (castellana)
ELEVEN_MODEL  = env("ELEVEN_MODEL", "eleven_multilingual_v2")
RESOLUTION    = env("RESOLUTION", "1920x1080")
CLIPS_SOURCE  = env("CLIPS_SOURCE", "pexels+pixabay")
MIN_CLIP_SEC  = int(env("MIN_CLIP_SEC", "3"))
ADD_MUSIC     = flag("ADD_MUSIC", "1")
USE_XFADE     = flag("USE_XFADE", "0")
MUSIC_URL     = env("MUSIC_URL", "")
ADD_SUBTITLES = flag("ADD_SUBTITLES", "0")
SUBS_STYLE    = env("SUBS_STYLE", "blanco")
MODO_PRUEBA   = flag("MODO_PRUEBA", "0")
TEST_BEATS    = int(env("TEST_BEATS", "6"))
PRIVACIDAD    = env("PRIVACIDAD_YOUTUBE", "private")
SUBIR_YT      = flag("SUBIR_YT", "1")
PLANES_DIR    = env("PLANES_DIR", "planes")
# Pista opcional de un guion concreto (modo manual). Si está vacío -> modo COLA:
# coge el siguiente .json pendiente de planes/ (los ya hechos están en planes/_hechos/).
PLAN_FILE_HINT = env("PLAN_FILE") or (sys.argv[1] if len(sys.argv) > 1 else None)

W, H = [int(x) for x in RESOLUTION.split("x")]
GAP = 0.35; FADE = 0.25; XF = 0.4
UA = {"User-Agent": "AnimalHistoryChannel/1.0 (educational)"}
GRADE = "eq=contrast=1.06:saturation=1.12:gamma=0.98,curves=preset=medium_contrast,vignette=PI/5,noise=alls=4:allf=t"

WORK = os.path.abspath(env("WORKDIR", "work"))
MED  = os.path.join(WORK, "media"); AUD = os.path.join(WORK, "audio"); SEG = os.path.join(WORK, "seg")
OUT  = os.path.abspath("out")

VIDEO_PLAN = {}       # se carga en main() (según el guion elegido)
SUBJECT = ""


# --------------------------------- UTILES ----------------------------------
def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("FFmpeg error:\n" + " ".join(cmd)[:300] + "\n" + p.stderr[-1200:])
    return p

def ffprobe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nokey=1:noprint_wrappers=1", path],
                         capture_output=True, text=True).stdout.strip()
    try: return float(out)
    except: return 0.0

def download(url, path):
    with requests.get(url, stream=True, timeout=120, headers=UA) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for c in r.iter_content(1 << 16): f.write(c)
    return path

def _order():
    o = []
    if CLIPS_SOURCE in ("pexels+pixabay", "pexels"): o.append("pexels")
    if CLIPS_SOURCE in ("pexels+pixabay", "pixabay"): o.append("pixabay")
    return o

def _queries(beat):
    qs = [q for q in ([beat.get("q")] + list(beat.get("syn", []))) if q]
    if SUBJECT:
        aug = [SUBJECT + " " + q for q in qs if SUBJECT.lower() not in q.lower()]
        qs = aug + qs
    seen = set(); out = []
    for q in qs:
        if q not in seen: seen.add(q); out.append(q)
    return out


# ------------------------------ CANDIDATOS VIDEO ------------------------------
def pexels_vid_cands(q):
    out = []
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": PEXELS_API_KEY},
                         params={"query": q, "per_page": 10, "orientation": "landscape", "size": "large"}, timeout=30)
        if r.status_code != 200: return out
        for vid in r.json().get("videos", []):
            dur = vid.get("duration", 0); best = None
            for f in vid.get("video_files", []):
                if f.get("file_type") == "video/mp4" and f.get("width", 0) >= 1280:
                    if best is None or f["width"] > best["width"]: best = f
            if best: out.append({"url": best["link"], "w": best.get("width", 0), "h": best.get("height", 0), "dur": dur, "src": "pexels"})
    except Exception as e: print("  pexels_vid:", str(e)[:60])
    return out

def pixabay_vid_cands(q):
    out = []
    try:
        r = requests.get("https://pixabay.com/api/videos/", params={"key": PIXABAY_API_KEY, "q": q, "video_type": "film", "per_page": 10, "order": "popular"}, timeout=30)
        if r.status_code != 200: return out
        for h in r.json().get("hits", []):
            dur = h.get("duration", 0); v = h.get("videos", {}); best = None
            for k in ("large", "medium", "small"):
                vv = v.get(k)
                if vv and vv.get("url") and (best is None or vv.get("width", 0) > best.get("width", 0)): best = vv
            if best: out.append({"url": best["url"], "w": best.get("width", 0), "h": best.get("height", 0), "dur": dur, "src": "pixabay"})
    except Exception as e: print("  pixabay_vid:", str(e)[:60])
    return out

def best_video(idx, queries):
    cands = []
    for q in queries:
        if not q: continue
        for src in _order():
            cands += pexels_vid_cands(q) if src == "pexels" else pixabay_vid_cands(q)
        if len([c for c in cands if c["dur"] >= 2]) >= 6: break
    good = [c for c in cands if c["dur"] >= 2 and c["w"] >= c["h"] and c["w"] >= 1280]
    good.sort(key=lambda c: (-(c["dur"] >= MIN_CLIP_SEC), -(c["w"] >= 1920), -c["w"], -c["dur"]))
    base = os.path.join(MED, f"m{idx}")
    for c in good[:5]:
        try:
            p = base + ".mp4"; download(c["url"], p)
            if ffprobe_dur(p) >= MIN_CLIP_SEC: return p
        except Exception as e: print("  vid dl:", str(e)[:60])
    return None


# --------------------------------- FOTOS -----------------------------------
def pexels_photo(q):
    try:
        r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": PEXELS_API_KEY},
                         params={"query": q, "per_page": 8, "orientation": "landscape", "size": "large"}, timeout=30)
        if r.status_code != 200: return None
        photos = r.json().get("photos", [])
        for p in photos:
            if p.get("width", 0) >= 1920 or p.get("height", 0) >= 1080:
                s = p.get("src", {}); u = s.get("large2x") or s.get("original") or s.get("large")
                if u: return u
        for p in photos:
            s = p.get("src", {}); u = s.get("large2x") or s.get("original") or s.get("large")
            if u: return u
    except Exception as e: print("  pexels_photo:", str(e)[:60])
    return None

def pixabay_photo(q):
    try:
        r = requests.get("https://pixabay.com/api/", params={"key": PIXABAY_API_KEY, "q": q, "per_page": 8, "image_type": "photo", "orientation": "horizontal", "min_width": 1600, "order": "popular"}, timeout=30)
        if r.status_code != 200: return None
        hits = r.json().get("hits", [])
        for h in hits:
            if h.get("imageWidth", 0) >= 1920: return h.get("largeImageURL") or h.get("webformatURL")
        if hits: return hits[0].get("largeImageURL") or hits[0].get("webformatURL")
    except Exception as e: print("  pixabay_photo:", str(e)[:60])
    return None

def wiki_image(title):
    try:
        r = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(title), timeout=30, headers=UA)
        if r.status_code == 200:
            j = r.json()
            th = (j.get("thumbnail") or {}).get("source")
            if th: return re.sub(r"/\d+px-", "/1280px-", th)
            orig = (j.get("originalimage") or {}).get("source")
            if orig and not orig.lower().endswith(".svg"): return orig
        r2 = requests.get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "generator": "search",
            "gsrsearch": title, "gsrnamespace": 6, "gsrlimit": 1, "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1280, "format": "json"}, timeout=30, headers=UA)
        if r2.status_code == 200:
            for p in r2.json().get("query", {}).get("pages", {}).values():
                ii = (p.get("imageinfo") or [{}])[0]
                if ii.get("thumburl") or ii.get("url"): return ii.get("thumburl") or ii.get("url")
    except Exception as e: print("  wiki_image:", str(e)[:60])
    return None

def best_photo(idx, queries):
    base = os.path.join(MED, f"m{idx}")
    for q in queries:
        if not q: continue
        for src in _order():
            u = pexels_photo(q) if src == "pexels" else pixabay_photo(q)
            if u:
                try:
                    p = base + ".img"; download(u, p)
                    if os.path.getsize(p) > 3000: return p
                except Exception as e: print("  photo dl:", str(e)[:60])
    return None

def fetch_visual(idx, beat):
    queries = _queries(beat)
    if beat.get("wiki"):
        u = wiki_image(beat["wiki"])
        if u:
            try:
                p = os.path.join(MED, f"m{idx}.img"); download(u, p)
                if os.path.getsize(p) > 3000: print(f"  Beat {idx}: foto Wikimedia -> {beat['wiki']}"); return p, "photo"
            except Exception as e: print("  wiki dl:", str(e)[:60])
    if beat.get("kind") == "photo":
        p = best_photo(idx, queries)
        if p: print(f"  Beat {idx}: foto stock"); return p, "photo"
    else:
        p = best_video(idx, queries)
        if p: print(f"  Beat {idx}: vídeo stock"); return p, "video"
        p = best_photo(idx, queries)
        if p: print(f"  Beat {idx}: foto (sin vídeo bueno)"); return p, "photo"
    print(f"  Beat {idx}: sin visual, fondo sólido"); return None, None


# ---------------------------------- VOZ ------------------------------------
def tts_beat(idx, text):
    mp3 = os.path.join(AUD, f"b{idx}.mp3"); wav = os.path.join(AUD, f"b{idx}.wav")
    body = {"text": text, "model_id": ELEVEN_MODEL, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
                      headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}, json=body, timeout=120)
    if r.status_code != 200: raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    with open(mp3, "wb") as f: f.write(r.content)
    run(["ffmpeg", "-y", "-i", mp3, "-ar", "44100", "-ac", "2", wav])
    return wav


# -------------------------------- MONTAJE ----------------------------------
def _fades(dur, xfade):
    if xfade: return ""
    fo = max(0.0, dur - FADE)
    return f",fade=t=in:st=0:d={FADE},fade=t=out:st={fo:.2f}:d={FADE}"

def seg_from_video(idx, clip, dur, xfade):
    out = os.path.join(SEG, f"s{idx}.mp4")
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setsar=1,{GRADE},format=yuv420p" + _fades(dur, xfade))
    run(["ffmpeg", "-y", "-stream_loop", "-1", "-t", f"{dur:.2f}", "-i", clip, "-an", "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", out])
    return out

def seg_from_photo(idx, img, dur, xfade):
    out = os.path.join(SEG, f"s{idx}.mp4"); frames = max(1, int(dur * 30)); comp = os.path.join(SEG, f"c{idx}.png")
    run(["ffmpeg", "-y", "-i", img, "-filter_complex",
         f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=22:1,eq=brightness=-0.08[bg];"
         f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1",
         "-frames:v", "1", comp])
    vf = (f"scale={W*2}:{H*2},zoompan=z='min(zoom+0.0007,1.12)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30,"
          f"{GRADE},format=yuv420p" + _fades(dur, xfade))
    run(["ffmpeg", "-y", "-loop", "1", "-i", comp, "-t", f"{dur:.2f}", "-r", "30", "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out])
    return out

def seg_solid(idx, dur, xfade):
    out = os.path.join(SEG, f"s{idx}.mp4")
    run(["ffmpeg", "-y", "-f", "lavfi", "-t", f"{dur:.2f}", "-i", f"color=c=0x0f141b:s={W}x{H}:r=30",
         "-vf", "format=yuv420p" + _fades(dur, xfade), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out])
    return out

def make_music(dur, path):
    if MUSIC_URL:
        try:
            tmp = os.path.join(WORK, "music_src"); download(MUSIC_URL, tmp)
            run(["ffmpeg", "-y", "-stream_loop", "-1", "-t", f"{dur:.2f}", "-i", tmp, "-af", "volume=0.18", "-ar", "44100", "-ac", "2", path]); return path
        except Exception as e: print("  música URL falló:", str(e)[:60])
    run(["ffmpeg", "-y", "-f", "lavfi", "-t", f"{dur:.2f}", "-i", "sine=frequency=110:sample_rate=44100",
         "-f", "lavfi", "-t", f"{dur:.2f}", "-i", "sine=frequency=146.83:sample_rate=44100",
         "-filter_complex", "[0][1]amix=inputs=2:normalize=0,lowpass=f=650,aecho=0.8:0.85:900:0.3,tremolo=f=0.10:d=0.5,volume=0.09[a]",
         "-map", "[a]", "-ar", "44100", "-ac", "2", path])
    return path

def _ts(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return ("%02d:%02d:%06.3f" % (h, m, s)).replace(".", ",")

def build_srt(beats, durs, path):
    t = 0.0; out = []
    for i, (b, d) in enumerate(zip(beats, durs), 1):
        out.append(str(i)); out.append(_ts(t) + " --> " + _ts(t + d)); out.append(b["narration"]); out.append("")
        t = t + d + GAP
    open(path, "w", encoding="utf-8").write("\n".join(out)); return path

def subs_style():
    col = "&H0000FFFF" if SUBS_STYLE == "amarillo" else "&H00FFFFFF"
    return "FontName=DejaVu Sans,Fontsize=16,Bold=1,PrimaryColour=" + col + ",OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=40"

def concat_plain(segs, out):
    lst = os.path.join(WORK, "v.txt"); open(lst, "w").write("".join(f"file '{v}'\n" for v in segs))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out]); return out

def concat_xfade(segs, seg_durs, out):
    if len(segs) == 1: shutil.copy(segs[0], out); return out
    inputs = []
    for s in segs: inputs += ["-i", s]
    fc = []; prev = "[0:v]"; off = seg_durs[0] - XF
    for i in range(1, len(segs)):
        lab = ("[vout]" if i == len(segs) - 1 else f"[x{i}]")
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}{lab}")
        prev = lab; off += seg_durs[i] - XF
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out])
    return out

def build_video():
    beats = VIDEO_PLAN["beats"]
    if MODO_PRUEBA:
        beats = beats[:max(1, int(TEST_BEATS))]; print(f"** MODO PRUEBA: {len(beats)} beats **")
    xfade = USE_XFADE
    seg_files = []; wavs = []; durs = []; seg_durs = []
    silence = os.path.join(AUD, "gap.wav")
    run(["ffmpeg", "-y", "-f", "lavfi", "-t", f"{GAP}", "-i", "anullsrc=r=44100:cl=stereo", silence])
    for i, b in enumerate(beats, 1):
        wavp = os.path.join(AUD, f"b{i}.wav"); segp = os.path.join(SEG, f"s{i}.mp4")
        if os.path.exists(wavp) and ffprobe_dur(wavp) > 0.1:
            wav = wavp; d = ffprobe_dur(wavp)
        else:
            print(f"[Beat {i}/{len(beats)}] {b['narration'][:46]}...")
            wav = tts_beat(i, b["narration"]); d = ffprobe_dur(wav)
        segd = d + GAP + (XF if xfade else 0.0)
        if os.path.exists(segp) and ffprobe_dur(segp) > 0.1:
            seg_files.append(segp)
        else:
            path, kind = fetch_visual(i, b)
            if kind == "video":   seg_files.append(seg_from_video(i, path, segd, xfade))
            elif kind == "photo": seg_files.append(seg_from_photo(i, path, segd, xfade))
            else:                 seg_files.append(seg_solid(i, segd, xfade))
        wavs.append(wav); durs.append(d); seg_durs.append(segd)

    visuals = os.path.join(WORK, "visuals.mp4")
    if xfade:
        try: concat_xfade(seg_files, seg_durs, visuals)
        except Exception as e:
            print("  xfade falló, uso corte con fundido:", str(e)[:120]); concat_plain(seg_files, visuals)
    else:
        concat_plain(seg_files, visuals)

    alst = os.path.join(WORK, "a.txt"); open(alst, "w").write("".join(f"file '{w}'\nfile '{silence}'\n" for w in wavs))
    narration = os.path.join(WORK, "narration.wav"); run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", alst, "-c", "copy", narration])
    final_audio = os.path.join(WORK, "audio.wav")
    if ADD_MUSIC:
        music = make_music(ffprobe_dur(narration), os.path.join(WORK, "music.wav"))
        run(["ffmpeg", "-y", "-i", narration, "-i", music, "-filter_complex",
             "[0:a]volume=1.0[v];[1:a]volume=1.0[m];[v][m]amix=inputs=2:duration=first:normalize=0[a]", "-map", "[a]", final_audio])
    else:
        shutil.copy(narration, final_audio)

    fecha = datetime.date.today().isoformat()
    base = VIDEO_PLAN.get("output_name") or SUBJECT or "video"
    out_name = f"{base}_{fecha}" + ("_PRUEBA" if MODO_PRUEBA else "") + ".mp4"
    out = os.path.join(OUT, out_name); subbed = False
    if ADD_SUBTITLES:
        try:
            srt = os.path.join(WORK, "subs.srt"); build_srt(beats, durs, srt)
            fc = "[0:v]subtitles=" + srt + ":force_style='" + subs_style() + "'[v]"
            run(["ffmpeg", "-y", "-i", visuals, "-i", final_audio, "-filter_complex", fc,
                 "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "192k", "-shortest", out]); subbed = True
        except Exception as e:
            print("  subtitulos fallaron, vídeo sin subs:", str(e)[:160])
    if not subbed:
        run(["ffmpeg", "-y", "-i", visuals, "-i", final_audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])
    print("\n✅ VÍDEO LISTO:", out, f"({ffprobe_dur(out):.1f}s) | subs: {subbed} | xfade: {xfade}")
    return out


# -------------------------------- MINIATURA --------------------------------
def build_thumbnail(mp4):
    try:
        from PIL import Image, ImageDraw, ImageFont
        YT = VIDEO_PLAN.get("youtube", {})
        thumb_text = (YT.get("thumb_text") or ((SUBJECT or "historia") + " en la guerra")).upper()
        thumb_sec = YT.get("thumb_sec")
        try:
            urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf", "/tmp/Anton.ttf")
        except Exception: pass

        def _font(sz):
            for p in ["/tmp/Anton.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
                if os.path.exists(p):
                    try: return ImageFont.truetype(p, sz)
                    except: pass
            return ImageFont.load_default()

        def _wrap(dr, txt, fn, mw):
            out, cur = [], ""
            for w in txt.split():
                t = (cur + " " + w).strip()
                if dr.textlength(t, font=fn) <= mw or not cur: cur = t
                else: out.append(cur); cur = w
            if cur: out.append(cur)
            return out

        frame = os.path.join(WORK, "_f.jpg")
        tsec = thumb_sec if thumb_sec is not None else max(1.0, ffprobe_dur(mp4) * 0.28)
        run(["ffmpeg", "-y", "-ss", f"{tsec}", "-i", mp4, "-frames:v", "1", "-q:v", "2", frame])
        im = Image.open(frame).convert("RGB"); TW, TH = 1280, 720
        r = max(TW / im.width, TH / im.height); im = im.resize((int(im.width * r), int(im.height * r)))
        im = im.crop(((im.width - TW) // 2, (im.height - TH) // 2, (im.width - TW) // 2 + TW, (im.height - TH) // 2 + TH))
        ov = Image.new("RGBA", (TW, TH), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        for i in range(430): d.line([(0, TH - 430 + i), (TW, TH - 430 + i)], fill=(0, 0, 0, int(205 * (i / 430) ** 1.3)))
        for i in range(520): d.line([(i, 0), (i, TH)], fill=(0, 0, 0, int(150 * (1 - i / 520) ** 1.4)))
        im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(im); fn = None; lines = None; LH = 0
        for sz in range(200, 60, -6):
            f = _font(sz); ls = _wrap(d, thumb_text, f, TW - 130); a, de = f.getmetrics()
            if len(ls) <= 3 and (a + de) * len(ls) <= 520: fn, lines, LH = f, ls, a + de; break
        if fn is None: fn = _font(90); lines = _wrap(d, thumb_text, fn, TW - 130); a, de = fn.getmetrics(); LH = a + de
        ty = TH - 70 - LH * len(lines); d.rectangle([70, ty - 34, 160, ty - 16], fill=(255, 190, 40))
        for ln in lines:
            d.text((66, ty), ln, font=fn, fill=(255, 255, 255), stroke_width=9, stroke_fill=(0, 0, 0)); ty += LH
        thumb = os.path.splitext(mp4)[0] + ".png"
        im.save(thumb, quality=92)
        print("✅ MINIATURA LISTA:", thumb)
        return thumb
    except Exception as e:
        print("⚠️ No se pudo crear la miniatura (el vídeo sí está bien):", e)
        return None


# ------------------------------ SUBIDA YOUTUBE ------------------------------
def subir_a_youtube(mp4, titulo, descripcion, tags, privacidad="private", thumb=None):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    # recorta tags para no pasar el límite de ~500 caracteres totales
    tags = tags or []
    acc, lim = [], 0
    for t in tags:
        lim += len(t) + 1
        if lim > 480: break
        acc.append(t)

    body = {
        "snippet": {"title": titulo[:100], "description": descripcion[:4900], "tags": acc, "categoryId": "27"},
        "status": {"privacyStatus": privacidad, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(mp4, chunksize=-1, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
    vid = resp["id"]
    if thumb and os.path.exists(thumb):
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb)).execute()
            print("  miniatura subida")
        except Exception as e:
            print("  no se pudo poner la miniatura por API (súbela a mano):", str(e)[:140])
    return f"https://youtu.be/{vid}", vid


# --------------------------- SELECCIÓN DE GUION (COLA) ----------------------
def pick_plan():
    """Guion concreto si se pasó PLAN_FILE; si no, el siguiente pendiente de planes/."""
    import glob
    if PLAN_FILE_HINT and os.path.exists(PLAN_FILE_HINT):
        return PLAN_FILE_HINT
    pend = sorted(glob.glob(os.path.join(PLANES_DIR, "*.json")))  # no entra en _hechos/
    return pend[0] if pend else None


# ---------------------------------- MAIN -----------------------------------
def main():
    global VIDEO_PLAN, SUBJECT
    for d in (WORK, MED, AUD, SEG, OUT): os.makedirs(d, exist_ok=True)
    for k, v in [("PEXELS_API_KEY", PEXELS_API_KEY), ("PIXABAY_API_KEY", PIXABAY_API_KEY), ("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY)]:
        if not v: sys.exit(f"ERROR: falta el Secret {k}.")

    plan_path = pick_plan()
    if not plan_path:
        sys.exit(f"COLA VACÍA: no hay guiones pendientes en {PLANES_DIR}/. Toca rellenar la cola.")
    VIDEO_PLAN = json.load(open(plan_path, encoding="utf-8"))
    SUBJECT = (VIDEO_PLAN.get("subject", "") or "").strip()

    print(f"Guion: {plan_path} | beats: {len(VIDEO_PLAN['beats'])} | voz: {VOICE_ID} | prueba: {MODO_PRUEBA}")
    mp4 = build_video()
    thumb = build_thumbnail(mp4)

    YT = VIDEO_PLAN.get("youtube", {})
    titulo = YT.get("title") or VIDEO_PLAN.get("title", "Documental")
    if YT.get("description"):
        desc = YT["description"]
    else:
        hook = " ".join(b.get("narration", "") for b in VIDEO_PLAN["beats"][:2]).strip()
        desc = hook + "\n\nSuscríbete para un nuevo documental cada semana."
    tags = YT.get("tags") or [SUBJECT, "historia", "documental", "historia animal"]

    print(f"\nTÍTULO: {titulo}")
    uploaded = False
    if SUBIR_YT and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN:
        print(f"Subiendo a YouTube como '{PRIVACIDAD}'...")
        url, vid = subir_a_youtube(mp4, titulo, desc, tags, PRIVACIDAD, thumb)
        uploaded = True
        print(f"✅ SUBIDO ({PRIVACIDAD}): {url}")
        print("   Revísalo en YouTube Studio y pásalo a Público cuando estés conforme.")
    else:
        print("ℹ️ Subida omitida (SUBIR_YT=0 o faltan credenciales de Google). El vídeo queda como artifact.")

    # Marca el guion como hecho SOLO si se subió y no es una prueba.
    # (El workflow hace luego git commit/push de este movimiento.)
    if uploaded and not MODO_PRUEBA:
        done_dir = os.path.join(PLANES_DIR, "_hechos"); os.makedirs(done_dir, exist_ok=True)
        dest = os.path.join(done_dir, os.path.basename(plan_path))
        try:
            shutil.move(plan_path, dest)
            print(f"🗂️  Guion hecho -> {dest}")
        except Exception as e:
            print("  no se pudo mover el guion a _hechos/:", e)

    print(f"\nArchivos en: {OUT}")


if __name__ == "__main__":
    main()
