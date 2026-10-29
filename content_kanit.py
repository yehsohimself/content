"""content_kanit.py - "bu video nasıl yapılmış" çözümlemesi için ek kanıtlar (2026-10-29, araştırma raporu
reports/Video yapılış çözümleme yöntemleri.md'nin hızlı kazançları).

- sarki_tani: şarkıyı sözlerden değil sesin kendisinden tanır (Shazam; resmi olmayan istemci, kırılabilir; sesin parmak izi Shazam'a gider).
  Tanımazsa müzik konuşmadan ayrılıp (Demucs) bir kez daha denenir.
- web_trend: şarkı adı ve TikTok'un önerdiği aramalarla açık web araması (DuckDuckGo), sonuç sayfaları okunur, Claude yalnız sayfaların
  söylediğini çıkarır: trend adı, orijinal an, araç. YouTube araması şarkıyı trende bağlamıyordu; web sayfaları bağlıyor (Özil vakası).
- izgaralar: sahne başına numaralı kare ızgaraları (saniyede en çok 6 kare); 16 tek kare yerine hareketi gösteren yoğun örnekleme.
- kademe: "hangi araç / hangi model" iddiasının gücü en güçlü kanıta göre (kesin → bilinmiyor); kod belirler, model değil.
"""
import asyncio
import html
import json
import re
import subprocess
from pathlib import Path

import content as C

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}


# ---------------------------------------------------------------- şarkı: sesten tanıma
async def _shazam(wav):
    from shazamio import Shazam
    return await asyncio.wait_for(Shazam().recognize(str(wav)), timeout=25)


def _shazam_tani(wav):
    import logging
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)          # istemcinin kapatılmayan oturum uyarıları (zararsız) günlüğü kirletmesin
    try:
        r = asyncio.run(_shazam(wav)) or {}
    except Exception:  # noqa: BLE001
        return {}
    tr = r.get("track") or {}
    if not tr.get("title"):
        return {}
    return {"sarki": tr.get("title"), "sanatci": tr.get("subtitle"), "kaynak": "shazam", "shazam": tr.get("url") or ""}


def sarki_tani(cid, konusma_var=False):
    """Videodaki şarkı (Shazam). Önce sesin tamamı; tanınmazsa ve videoda konuşma varsa müzik ayrılıp yeniden. Bulamazsa {}.
    Ayarlar'da açık değilse hiç çalışmaz (ses parmak izi Shazam'a gider)."""
    if not C.ayar().get("shazam"):
        return {}
    klasor = C.yol(cid) / "is_ara"
    klasor.mkdir(exist_ok=True)
    wav = klasor / "ses16.wav"
    subprocess.run([C.FFMPEG, "-y", "-v", "error", "-i", str(C.yol(cid) / "kaynak.mp4"), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                   capture_output=True, timeout=60)
    if not wav.exists():
        return {}
    s = _shazam_tani(wav)
    if s or not konusma_var:
        return s
    try:                                                           # konuşma müziği örtüyorsa: Demucs ile müziği ayır, tekrar dene
        import dublaj
        _, muzik = dublaj._ayir(C.yol(cid) / "kaynak.mp4", klasor, lambda m: None)
        if muzik:
            s = _shazam_tani(muzik)
            if s:
                s["kaynak"] = "shazam (müzik ayrılarak)"
    except Exception:  # noqa: BLE001
        pass
    return s


# ---------------------------------------------------------------- web: trend sayfaları
ATLA = re.compile(r"youtube\.com|youtu\.be|instagram\.com|tiktok\.com|facebook\.com|spotify\.com|music\.apple|soundcloud\.com|shazam\.com|"
                  r"genius\.com|musixmatch|lyrics|deezer\.com|bilibili|pinterest\.|x\.com|twitter\.com|reddit\.com/r/[^/]+/?$", re.I)


WEB_TREND = """Search the web (WebSearch, then WebFetch the best 2-4 pages) to identify the short-video TREND this TikTok/Reels video belongs to.
Known about the video: {bilinen}
Its sound: {ses}. The video itself may be a one-off VARIATION (other characters, other setting) of a trend that uses this sound; identify the trend
built on this sound (or on the search ideas), even if no page mentions this exact video.
Search ideas: {sorgular}
Look for: trend explainer pages, news articles, Know Your Meme, AI-video sites' trend/template pages ("<song> AI trend", "<trend> vs original").
Report ONLY what pages explicitly say; never guess. Vendor pages may exaggerate tools but their facts (which match/film/date/song) are usually right.
If no page clearly describes a trend that uses this sound/search idea, return "bulundu": false.
Reply with JSON only, values in {dil_ad}:
{{"bulundu": true, "akim": "trend name", "orijinal_an": "the real moment it recreates (who, what, which match/film, date) or empty",
"araclar": ["tools/models the pages name"], "nasil": "how it is made according to the pages, 1-3 sentences",
"arama": "one YouTube query to find the original moment, or empty", "kaynaklar": [{{"link": "page URL", "ne": "what this page says, short"}}]}}"""


def web_trend(sarki, oneriler=(), eylem="", bilinen="", dil="tr"):
    """Akımı web'de arar: Claude'un kendi web araması (WebSearch/WebFetch; abonelikten, ek ücret yok). Anahtarsız arama motorları
    (DuckDuckGo, Bing) otomatik sorguyu birkaç istekte engelliyor, bu yüzden onlar yalnız yedek. Bulamazsa {}."""
    import claude_yaz
    sanatci = ""
    if isinstance(sarki, dict):
        sanatci, sarki = sarki.get("sanatci") or "", sarki.get("sarki") or ""
    sarki = re.sub(r"\s*[\(\[].*?[\)\]]", "", sarki or "").strip()   # "Clandestina (Cover)" → "Clandestina"
    sorgular = []
    if sarki:
        sorgular += [f'"{sarki}" AI trend', f"{sarki} tiktok trend"]
        if eylem:
            sorgular.append(f"{sarki} {eylem}")
    sorgular += [f"{w} trend" for w in list(oneriler)[:2] if w]
    if not sorgular:
        return {}
    try:
        j = claude_yaz.json_coz(claude_yaz.sor(WEB_TREND.format(dil_ad="English" if dil == "en" else "Turkish", bilinen=bilinen[:900] or "-", sorgular="; ".join(dict.fromkeys(sorgular)),
                                                                   ses=f"{sarki} – {sanatci}".strip(" –") or "unknown"),
                                               model_adi="sonnet", araclar="WebSearch,WebFetch", zaman_asimi=300)) or {}
    except Exception:  # noqa: BLE001
        j = {}
    if not j.get("bulundu"):
        return {}
    j["kaynaklar"] = [k for k in j.get("kaynaklar") or [] if isinstance(k, dict) and re.match(r"https?://", k.get("link") or "")
                      and not ATLA.search(k.get("link") or "")][:5]
    return j


REPLIK = """The short video below shows these characters/visuals: {bilinen}
Its speech (automatic transcript, may contain errors): "{ses}"
Question: do these spoken lines come from an EXISTING film, TV series, or famous clip? Short AI videos often take a real film scene, keep its
ORIGINAL audio, and only replace the faces (face swap / character replace) with other characters, so the visible characters may be from a
different show than the audio. Search the web (WebSearch; quote 4-8 word distinctive fragments of the lines, try with and without quotes, try
subtitle sites, quote/replik sites, YouTube titles; then WebFetch the best pages) to identify the source of THE AUDIO.
Report ONLY what pages show; never guess a title. If no page contains these lines, "bulundu": false.
Reply with JSON only, values in {dil_ad}:
{{"bulundu": true, "eser": "film/series title", "yil": "year or empty", "sahne": "which scene/characters/actors, short", "link": "best page or video URL",
"kaynaklar": [{{"link": "URL", "ne": "what this page shows, short"}}]}}"""


def replik_ara(ses, bilinen="", dil="tr"):
    """Konuşma mevcut bir filmden/diziden mi? Repliklerin parçalarını Claude'un web aramasıyla arar (yüz değiştirme akımlarında ses
    çoğu zaman orijinal filmin sesidir). Konuşma kısaysa ya da bulunamazsa {}."""
    import claude_yaz
    ses = re.sub(r"\s+", " ", ses or "").strip()
    if len(re.findall(r"\w+", ses)) < 15:
        return {}
    try:
        j = claude_yaz.json_coz(claude_yaz.sor(REPLIK.format(dil_ad="English" if dil == "en" else "Turkish", bilinen=bilinen[:600] or "-", ses=ses[:1200]),
                                               model_adi="sonnet", araclar="WebSearch,WebFetch", zaman_asimi=300)) or {}
    except Exception:  # noqa: BLE001
        return {}
    if not j.get("bulundu") or not j.get("eser"):
        return {}
    j["kaynaklar"] = [k for k in j.get("kaynaklar") or [] if isinstance(k, dict) and re.match(r"https?://", k.get("link") or "")][:5]
    return j

# ---------------------------------------------------------------- TikTok: sayfanın ek alanları
def tiktok_ek(it):
    """sayfa_kaniti'nin henüz okumadığı alanlar: TikTok'un kendi içerik sınıfı, yapay zekâ etiket türü, şarkı eşleşmesi, otomatik altyazı."""
    import requests
    k = {}
    if it.get("diversificationLabels"):
        k["tiktok_sinifi"] = it["diversificationLabels"]
    tip = it.get("aigcLabelType")
    if tip and str(tip) != "0":
        k["yapay_zeka_etiket_turu"] = {"1": "TikTok otomatik etiketledi", "2": "yükleyen 'yapay zekâ ile üretildi' dedi"}.get(str(tip), str(tip))
    mu = it.get("music") or {}
    dsp = [f"{s.get('title') or s.get('song_name') or ''} – {s.get('author') or s.get('artist_name') or ''}".strip(" –")
           for s in ((mu.get("tt2dsp") or {}).get("tt_to_dsp_song_infos") or [])]
    if [d for d in dsp if d]:
        k["tiktok_sarki_eslesmesi"] = [d for d in dsp if d][:3]
    for c in ((it.get("video") or {}).get("claInfo") or {}).get("captionInfos") or []:
        try:
            t = requests.get(c.get("url"), headers={**UA, "Referer": "https://www.tiktok.com/"}, timeout=15).text
        except Exception:  # noqa: BLE001
            continue
        satir = [l.strip() for l in t.splitlines() if l.strip() and "-->" not in l and not l.startswith(("WEBVTT", "NOTE")) and not l.strip().isdigit()]
        if satir:
            k["tiktok_altyazisi"] = {"dil": c.get("language"), "metin": " ".join(satir)[:1200]}
            break
    for a in it.get("anchors") or []:
        try:
            ek = json.loads(a.get("logExtra") or "{}")
        except Exception:  # noqa: BLE001
            continue
        if ek.get("capability_key") and ek["capability_key"] != "none":
            k["capcut_ozelligi"] = ek["capability_key"]
        if ek.get("anchor_type_level2"):
            k["baglanti_alt_turu"] = ek["anchor_type_level2"]
    return k


# ---------------------------------------------------------------- kareler: sahne başına numaralı ızgara
def izgaralar(cid, butce=96, en_cok=8):
    """Sahne başına numaralı kare ızgaraları (4x3, her karede 'S{sahne} · {sn}'). Kısa videoda saniyede 6 kareye kadar.
    Araştırma: ızgara + kare numarası, eğitimsiz resim modellerinde video anlamayı belirgin iyileştiriyor (IG-VLM, NumPro)."""
    from PIL import Image, ImageDraw, ImageFont
    d = C.oku(cid)
    sure = float((d.get("kaynak") or {}).get("sure") or 0)
    if sure <= 0:
        return []
    sahneler = (d.get("tarif") or {}).get("sahneler") or [{"no": 1, "bas": 0, "bit": sure}]
    fps = max(0.5, min(6.0, butce / sure))
    klasor = C.yol(cid) / "is_ara" / "izgara"
    klasor.mkdir(parents=True, exist_ok=True)
    for f in klasor.glob("*.jpg"):
        f.unlink()
    ham = klasor / "ham"
    ham.mkdir(exist_ok=True)
    for f in ham.glob("*.jpg"):
        f.unlink()
    subprocess.run([C.FFMPEG, "-y", "-v", "error", "-i", str(C.yol(cid) / "kaynak.mp4"), "-vf", f"fps={fps:.3f},scale=320:-2",
                    "-q:v", "4", str(ham / "k_%04d.jpg")], capture_output=True, timeout=180)
    kareler = sorted(ham.glob("k_*.jpg"))
    if not kareler:
        return []
    try:
        yazi = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20)
    except Exception:  # noqa: BLE001
        yazi = ImageFont.load_default()

    def sahne_no(sn):
        for s in sahneler:
            if s["bas"] - 0.05 <= sn < s["bit"] + 0.05:
                return s["no"]
        return sahneler[-1]["no"]

    gruplar, simdiki, son = [], [], None
    for i, f in enumerate(kareler):
        sn = i / fps
        no = sahne_no(sn)
        if (son is not None and no != son and len(simdiki) >= 4) or len(simdiki) == 12:
            gruplar.append(simdiki)
            simdiki = []
        simdiki.append((f, sn, no))
        son = no
    if simdiki:
        gruplar.append(simdiki)
    if len(gruplar) > en_cok:                                      # çok uzun videolarda: eşit aralıklı en_cok ızgara
        gruplar = [gruplar[round(i * (len(gruplar) - 1) / (en_cok - 1))] for i in range(en_cok)]
    out = []
    for gi, g in enumerate(gruplar):
        ilk = Image.open(g[0][0])
        w, h = ilk.size
        sutun = 4 if len(g) > 6 else 3
        satir = -(-len(g) // sutun)
        tuval = Image.new("RGB", (sutun * w, satir * h), (0, 0, 0))
        c = ImageDraw.Draw(tuval)
        for j, (f, sn, no) in enumerate(g):
            x, y = (j % sutun) * w, (j // sutun) * h
            tuval.paste(Image.open(f).resize((w, h)), (x, y))
            etiket = f"S{no} · {sn:.1f}s"
            c.rectangle([x, y, x + 12 * len(etiket) + 8, y + 26], fill=(0, 0, 0))
            c.text((x + 4, y + 2), etiket, fill=(255, 230, 0), font=yazi)
        f = klasor / f"izgara_{gi + 1:02d}.jpg"
        tuval.save(f, quality=82)
        out.append(f)
    return out


# ---------------------------------------------------------------- kanıt kademesi
KADEME_AD = {5: "kesin", 4: "neredeyse kesin", 3: "güçlü olasılık", 2: "olası", 1: "bilinmiyor"}
PLATFORM = re.compile(r"^\s*(tiktok|instagram|youtube|reels|shorts)\b(?!.*(şablon|template|efekt|effect|filtre))", re.I)
DAYANAK_PUAN = {"platform": 5, "sahip": 5, "dosya": 5, "logo": 4, "ogretici": 3, "web": 3, "yorum": 2, "reklam": 2, "olcum": 2, "gorsel": 1}


def kademe(y, sayfa, dosya, ogr, web):
    """Araç/model iddialarının gücünü en güçlü kanıta göre belirler; model 'kesin' dese bile dayanağı görselse 'bilinmiyor'a iner.
    Ayrıca bulunamayan kanıtları yazar: 'olası' kelimesi hak edilmiş görünsün."""
    en = 1
    for a in y.get("araclar") or []:
        p = DAYANAK_PUAN.get(str(a.get("dayanak") or "gorsel").lower(), 1)
        if p >= 5 and not (sayfa.get("baglantilar") or dosya.get("yapay_zeka_etiketi_dosyada") or a.get("dayanak") == "sahip"):
            p = 3                                                  # platform/dosya dediği halde sayfada/dosyada karşılığı yoksa
        if p == 3 and a.get("dayanak") == "ogretici" and not ogr:
            p = 1
        if p == 3 and a.get("dayanak") == "web" and not web:
            p = 1
        a["kademe"] = KADEME_AD[p]
        a["kesin"] = p >= 4
        if not PLATFORM.search(a.get("ad") or ""):                 # "TikTok'a yüklendi" yapılış aracı değil; genel kademeyi o belirlemez
            en = max(en, p)
    y["kademe"] = KADEME_AD[en]
    if en <= 2 and y.get("guven") == "yuksek":
        y["guven"] = "orta"
    if en == 1:
        y["guven"] = "dusuk"
    yok = []
    if not sayfa.get("baglantilar"):
        yok.append("Platform sayfasında şablon ya da araç bağlantısı yok")
    if not (sayfa.get("yapay_zeka_etiketi") or sayfa.get("yapay_zeka_etiket_turu") or dosya.get("yapay_zeka_etiketi_dosyada")):
        yok.append("Platformda ve dosyada yapay zekâ etiketi yok (bu, yapay zekâ kullanılmadığını göstermez)")
    if not ogr:
        yok.append("Aynı akımı anlatan öğretici video bulunamadı")
    if not web:
        yok.append("Web'de bu akımı anlatan bir sayfa bulunamadı")
    y["bulunamayanlar"] = yok
    return y
