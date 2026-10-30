"""content_benzer.py - "aynı sesle / benzer görüntüyle başka ne üretilmiş?" (2026-10-30).

Uzman bir kurgucunun ilk yaptığı iş: sesi aratır, aynı sesle yapılmış başka videolara bakar. Akımlarda yöntem hep aynıdır: bir görüntünün
üstündeki kişiler değiştirilir, bazen ses dublajlanır, bazen ortam değişir; kaynak bazen videodur bazen tek bir fotoğraf. Aynı sesi taşıyan
kopyalar yan yana konunca SABİT olan (şablon/akım: ses, hareket, kurgu) ile DEĞİŞEN (kişi, dünya, dil) ayrılır; yöntem bundan okunur.

- adaylar(): şarkı/akım/şablon adı ve TikTok'un önerdiği aramalarla YouTube'da benzer kısa videolar (≤120 sn, en çok 6); TikTok'un kendi "aynı ses"
  sayfası imzasız boş döndüğü için YouTube kullanılır. TikTok'un verdiği özgün ses dosyası (music.playUrl) da indirilip videonun sesiyle karşılaştırılır.
- karsilastir(): ses benzerliği = RMS zarfı çapraz ilişkisi (±6 sn kayma); görüntü benzerliği = macOS Vision görsel parmak izi (VNGenerateImageFeaturePrint,
  768 boyut, kosinüs; aynı video 1,00, aynı kompozisyon ~0,8, farklı ~0,3). Model indirilmez, bulut yok.
- yan yana kare şeridi (üst: bu video, alt: benzer video; zaman yüzdesine göre hizalı) Claude'a "ortak olan ne, değişen ne" diye gösterilir.
"""
import json
import re
import subprocess
from pathlib import Path

import content as C

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
EN_COK = 6
KARE = 6                     # şeritte kare sayısı


# ---------------------------------------------------------------- ses: RMS zarfı
def _zarf(ses_dosyasi, hz=20, en_cok_sn=120.0):
    """Sesin RMS zarfı (saniyede `hz` örnek, en çok `en_cok_sn`); okunamazsa None."""
    import numpy as np
    r = subprocess.run([C.FFMPEG, "-v", "error", "-i", str(ses_dosyasi), "-t", str(en_cok_sn), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                       capture_output=True, timeout=120)
    x = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32)
    if x.size < 8000:
        return None
    adim = 8000 // hz
    n = x.size // adim
    z = np.sqrt((x[:n * adim].reshape(n, adim) ** 2).mean(axis=1))
    z = z - z.mean()
    s = z.std()
    return z / s if s > 1e-6 else None


def ses_benzerligi(a, b, hz=20, kayma_sn=6.0):
    """İki ses zarfının en iyi çapraz ilişkisi (−1..1) ve kayma (sn). Kısa olan uzununun içinde kaydırılarak aranır."""
    import numpy as np
    if a is None or b is None:
        return 0.0, 0.0
    if a.size < b.size:
        a, b, ters = b, a, True
    else:
        ters = False
    k = int(kayma_sn * hz)
    en, en_kayma = -1.0, 0
    for ofs in range(-k, max(k, a.size - b.size) + 1):
        bas, bit = max(0, ofs), min(a.size, ofs + b.size)
        if bit - bas < hz * 3:
            continue
        pa, pb = a[bas:bit], b[bas - ofs:bit - ofs]
        c = float((pa * pb).mean() / (pa.std() * pb.std() + 1e-6))
        if c > en:
            en, en_kayma = c, ofs
    return round(max(-1.0, min(1.0, en)), 3), round((-en_kayma if ters else en_kayma) / hz, 2)


# ---------------------------------------------------------------- görüntü: Vision parmak izi
def _parmak_izi(yol):
    import numpy as np
    import Quartz
    import Vision
    from Foundation import NSURL
    img = Quartz.CIImage.imageWithContentsOfURL_(NSURL.fileURLWithPath_(str(yol)))
    if img is None:
        return None
    h = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(img, None)
    r = Vision.VNGenerateImageFeaturePrintRequest.alloc().init()
    h.performRequests_error_([r], None)
    s = r.results()
    if not s:
        return None
    v = np.frombuffer(bytes(s[0].data()), dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n > 0 else None


def _kareler(video, klasor, n=KARE, sure=None):
    """Videodan zaman yüzdesine göre n kare (320 px)."""
    klasor.mkdir(parents=True, exist_ok=True)
    if not sure:
        sure = C.bilgi(video)["sure"]
    out = []
    for i in range(n):
        t = max(0.2, sure * (i + 0.5) / n)
        f = klasor / f"k_{i}.jpg"
        subprocess.run([C.FFMPEG, "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "4", str(f)],
                       capture_output=True, timeout=30)
        if f.exists():
            out.append(f)
    return out


def gorsel_benzerligi(kareler_a, kareler_b):
    """Her A karesi için en yakın B karesinin kosinüsü; ortalaması (0..1) ve en yüksek eşleşme. Kare çıkmazsa (0, 0)."""
    import numpy as np
    A = [v for v in (_parmak_izi(k) for k in kareler_a) if v is not None]
    B = [v for v in (_parmak_izi(k) for k in kareler_b) if v is not None]
    if not A or not B:
        return 0.0, 0.0
    M = np.array(A) @ np.array(B).T
    return round(float(M.max(axis=1).mean()), 3), round(float(M.max()), 3)


def serit(kareler_ust, kareler_alt, hedef, etiket_ust="Bu video", etiket_alt="Benzer video"):
    """İki sıra kare: üstte bu video, altta benzer video; aynı sütun = aynı zaman yüzdesi."""
    from PIL import Image, ImageDraw, ImageFont
    if not kareler_ust or not kareler_alt:
        return None
    try:
        yazi = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18)
    except Exception:  # noqa: BLE001
        yazi = ImageFont.load_default()
    w, h = 180, 320
    n = max(len(kareler_ust), len(kareler_alt))
    tuval = Image.new("RGB", (n * w, 2 * h + 56), (0, 0, 0))
    c = ImageDraw.Draw(tuval)
    for satir, (kareler, etiket) in enumerate(((kareler_ust, etiket_ust), (kareler_alt, etiket_alt))):
        y0 = satir * (h + 28)
        c.text((6, y0 + 4), etiket, fill=(255, 230, 0), font=yazi)
        for j, k in enumerate(kareler[:n]):
            im = Image.open(k).convert("RGB")
            im.thumbnail((w, h))
            tuval.paste(im, (j * w + (w - im.width) // 2, y0 + 28 + (h - im.height) // 2))
    tuval.save(hedef, quality=82)
    return hedef


# ---------------------------------------------------------------- adaylar
def _ara(sorgu, gor, en_sure=120):
    out = []
    try:
        r = subprocess.run([C.YTDLP, "--flat-playlist", "--no-warnings", "--print", "%(id)s\t%(title)s\t%(channel)s\t%(duration)s\t%(view_count)s",
                            f"ytsearch10:{sorgu}"], capture_output=True, text=True, timeout=90)
    except Exception:  # noqa: BLE001
        return out
    for l in r.stdout.splitlines():
        p = l.split("\t")
        if len(p) < 5 or p[0] in gor:
            continue
        try:
            sure = float(p[3])
        except ValueError:
            continue
        if not 4 <= sure <= en_sure:
            continue
        gor.add(p[0])
        out.append({"id": p[0], "baslik": p[1][:120], "kanal": p[2], "sure": int(sure), "izlenme": p[4], "link": f"https://www.youtube.com/watch?v={p[0]}",
                    "sorgu": sorgu})
    return out


def adaylar(d, sarki=None, web=None, sayfa=None, en_cok=EN_COK):
    """Benzer kısa video adayları: şarkı adı, akım adı, şablon adı, TikTok'un önerdiği aramalar, başlığın ilk sözcükleri."""
    sayfa, web, sarki = sayfa or {}, web or {}, sarki or {}
    sorgular = []
    sad = re.sub(r"\s*[\(\[].*?[\)\]]", "", str(sarki.get("sarki") or "")).strip()
    if sad and sad.lower() not in ("original sound", "som original", "nothing"):
        sorgular += [f"{sad} tiktok #shorts", f"{sad} trend"]
    if web.get("akim"):
        sorgular.append(f"{web['akim'][:60]} #shorts")
    for b in sayfa.get("baglantilar") or []:
        ad = ((b.get("sablon") or {}).get("ad") or "").strip()
        if ad:
            sorgular.append(f"{ad} capcut template")
    sorgular += [f"{w} #shorts" for w in (sayfa.get("tiktok_onerilen_aramalar") or [])[:2]]
    baslik = ((d.get("kaynak") or {}).get("baslik") or "").strip()
    if baslik and baslik != "(gizli)":
        sorgular.append(" ".join(re.findall(r"\w+", baslik)[:6]) + " #shorts")
    gor = set()
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", d.get("link") or "")
    if m:
        gor.add(m.group(1))
    out = []
    for q in list(dict.fromkeys(q for q in sorgular if q.strip()))[:4]:
        out += _ara(q, gor)
        if len(out) >= en_cok * 2:
            break
    return out[:en_cok]


def _indir(aday, klasor):
    f = klasor / f"{aday['id']}.mp4"
    if f.exists() and f.stat().st_size > 10000:
        return f
    try:
        subprocess.run([C.YTDLP, "--no-playlist", "--no-warnings", "-q", "-f", "bv*[height<=360][ext=mp4]+ba[ext=m4a]/bv*[height<=360]+ba/b[height<=480]/b",
                        "--merge-output-format", "mp4", "--max-filesize", "60M", "-o", str(f), aday["link"]], capture_output=True, timeout=240)
    except Exception:  # noqa: BLE001
        return None
    return f if f.exists() and f.stat().st_size > 10000 else None


def ozgun_ses(cid, sayfa):
    """TikTok'un verdiği özgün ses dosyası (music.playUrl) indirilip videonun sesiyle karşılaştırılır: ses başka bir videodan alınmışsa akımın
    sesidir. {sahibi, ad, benzerlik} ya da {}."""
    mu = (sayfa or {}).get("muzik") or {}
    url = mu.get("ses_dosyasi")
    if not url:
        return {}
    import requests
    klasor = C.yol(cid) / "is_ara" / "benzer"
    klasor.mkdir(parents=True, exist_ok=True)
    f = klasor / "ozgun_ses.mp3"
    try:
        r = requests.get(url, headers={**UA, "Referer": "https://www.tiktok.com/"}, timeout=30)
        if not r.ok or len(r.content) < 5000:
            return {}
        f.write_bytes(r.content)
    except Exception:  # noqa: BLE001
        return {}
    b, _ = ses_benzerligi(_zarf(C.yol(cid) / "kaynak.mp4"), _zarf(f))
    return {"sahibi": mu.get("sahibi"), "ad": mu.get("ad"), "ozgun": bool(mu.get("ozgun_ses")), "benzerlik": b}


def karsilastir(cid, sarki=None, web=None, sayfa=None, en_cok=EN_COK):
    """Benzer videoları bulur, indirir, ses ve görüntü benzerliğini ölçer, yan yana şeritleri çizer.
    Döner: [{link, baslik, kanal, sure, ses, kayma, gorsel, gorsel_en, serit, yorum}] (en benzerden)."""
    klasor = C.yol(cid) / "is_ara" / "benzer"
    klasor.mkdir(parents=True, exist_ok=True)
    kaynak = C.yol(cid) / "kaynak.mp4"
    d = C.oku(cid) or {}
    hedef_zarf = _zarf(kaynak)
    hedef_kareler = _kareler(kaynak, klasor / "bu", sure=(d.get("kaynak") or {}).get("sure"))
    out = []
    for a in adaylar(d, sarki, web, sayfa, en_cok):
        v = _indir(a, klasor)
        if not v:
            continue
        ses, kayma = ses_benzerligi(hedef_zarf, _zarf(v))
        kareler = _kareler(v, klasor / a["id"])
        gorsel, gorsel_en = gorsel_benzerligi(hedef_kareler, kareler)
        s = serit(hedef_kareler, kareler, klasor / f"serit_{a['id']}.jpg", etiket_alt=f"Benzer: {a['baslik'][:60]}")
        out.append({**a, "ses": ses, "kayma": kayma, "gorsel": gorsel, "gorsel_en": gorsel_en, "serit": str(s) if s else "", "yorum": yorum(ses, gorsel, gorsel_en)})
    out.sort(key=lambda x: -(x["ses"] * 0.6 + x["gorsel"] * 0.4))
    return out


def yorum(ses, gorsel, gorsel_en):
    """Ölçülerin düz Türkçe karşılığı (istemde ve sayfada)."""
    s = "ses aynı" if ses >= 0.6 else "ses benzer" if ses >= 0.35 else "ses farklı"
    g = ("görüntü aynı (aynı çekim)" if gorsel >= 0.9 else "görüntü çok benzer (aynı kurgu/kompozisyon, ayrıntılar farklı)" if gorsel >= 0.75
         else "benzer kareler var" if gorsel_en >= 0.8 else "görüntü farklı")
    return f"{s}, {g}"


def istem_metni(liste, ozgun=None):
    """ISTEM'e giren özet."""
    satir = []
    if ozgun and ozgun.get("sahibi"):
        if ozgun.get("benzerlik", 0) >= 0.6:
            satir.append(f"Platformun özgün ses kaydı (@{ozgun['sahibi']}, '{ozgun.get('ad')}') bu videonun sesiyle AYNI; ses o hesaptan alınmış"
                         + (" (video sahibi başka hesap ise ses başkasının videosundan)." if ozgun.get("ozgun") else "."))
        else:
            satir.append(f"Platform özgün ses olarak @{ozgun['sahibi']} '{ozgun.get('ad')}' gösteriyor; zarf benzerliği {ozgun.get('benzerlik')}.")
    for b in liste:
        satir.append(f"- [{b['baslik']}] {b['link']} ({b['kanal']}, {b['sure']} sn): {b['yorum']} (ses {b['ses']}, görüntü {b['gorsel']}/{b['gorsel_en']})")
    return "\n".join(satir) if satir else "(benzer video bulunamadı)"
