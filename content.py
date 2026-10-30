"""content.py - Content: bir videonun linki → nasıl yapıldığı ve adım adım nasıl yapılacağı (2026-10-23; 2026-10-29 sade sürüm).

Content video üretmez (28 Ekim'de üretim kapatıldı, kodu 29 Ekim'de çıkarıldı). Akış:
  cozumle(cid) → content/<cid>/kaynak.mp4, ses yazısı (sesnot.py), kesmeler (PySceneDetect + ffmpeg), kareler + ekran yazısı (Apple Vision)
                 → Claude (görsel) "tarif" (videoda ne oluyor, sahneler) → content_yontem.coz(cid): kanıtlar, yöntem ve adım adım rehber.
Her adım is.json'a yazar; yarıda kesilen iş "Tekrar dene" ile kaldığı yerden sürer (inmiş video ve tarif yeniden yapılmaz).

Ayarlar `content/ayarlar.json` (ayar()): yorumlar (TikTok yorumlarını oku), shazam (şarkıyı sesten tanı; parmak izi Shazam'a gider),
tarayici (indirme olmazsa tarayıcı oturumuyla dene: "chrome", "safari"... ya da boş), sunra (güncel model adları listesi), dil (tr | en).
Veri klasörü CONTENT_KOK ortam değişkeniyle değiştirilebilir (testler geçici klasör kullanır).
Elle: python content.py coz <link> ["istek"]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

KLASOR = Path(__file__).resolve().parent
sys.path.insert(0, str(KLASOR))
KOK = Path(os.environ.get("CONTENT_KOK") or KLASOR / "content")
PYTHON = str(KLASOR / ".venv" / "bin" / "python")
YTDLP = str(KLASOR / ".venv" / "bin" / "yt-dlp") if (KLASOR / ".venv" / "bin" / "yt-dlp").exists() else (shutil.which("yt-dlp") or "yt-dlp")
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

AYAR_VARSAYILAN = {"yorumlar": False, "shazam": False, "tarayici": "", "sunra": True, "dil": ""}
TARAYICILAR = ("chrome", "safari", "firefox", "brave", "edge", "arc")

_kilit = threading.RLock()      # oku+değiştir+yaz bir bütün


def ayar():
    try:
        return {**AYAR_VARSAYILAN, **json.loads((KOK / "ayarlar.json").read_text(encoding="utf-8"))}
    except Exception:  # noqa: BLE001
        return dict(AYAR_VARSAYILAN)


def ayar_yaz(yeni):
    a = ayar()
    for k, v in (yeni or {}).items():
        if k in ("yorumlar", "shazam", "sunra"):
            a[k] = bool(v)
        elif k == "tarayici":
            a[k] = v if v in TARAYICILAR else ""
        elif k == "dil":
            a[k] = v if v in ("tr", "en") else ""
    KOK.mkdir(parents=True, exist_ok=True)
    (KOK / "ayarlar.json").write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    return a


def yol(cid):
    if not re.fullmatch(r"[a-f0-9]{10}", str(cid or "")):
        raise ValueError("geçersiz iş")
    return KOK / cid


def oku(cid):
    try:
        return json.loads((yol(cid) / "is.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def yaz(cid, d):
    with _kilit:
        p = yol(cid) / "is.json"
        t = p.with_suffix(".tmp")
        t.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        t.replace(p)


def degistir(cid, fn):
    with _kilit:
        d = oku(cid) or {}
        fn(d)
        yaz(cid, d)
        return d


def guncelle(cid, **alan):
    return degistir(cid, lambda d: d.update(alan))


def log(cid, m):
    print(f"[content {cid}] {m}", flush=True)

    def fn(d):
        d["log"] = (d.get("log") or [])[-59:] + [[round(time.time()), m]]
        d["adim"] = m
    degistir(cid, fn)


def yeni(link, istek, **ek):
    cid = uuid.uuid4().hex[:10]
    (KOK / cid).mkdir(parents=True, exist_ok=True)
    yaz(cid, {"id": cid, "link": link.strip(), "istek": (istek or "").strip(), "olusma": time.time(), "durum": "cozuluyor",
              "adim": "Başlıyor", "log": [], **ek})
    return cid


def liste(n=40):
    out = []
    for p in sorted(KOK.glob("*/is.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if len(out) >= n:
            break
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if d.get("silindi") or d.get("radar") or d.get("test") or not d.get("id"):
            continue
        y = d.get("yontem") or {}
        out.append({"id": d["id"], "baslik": (d.get("kaynak") or {}).get("baslik") or d.get("link"), "istek": d.get("istek"),
                    "durum": d.get("durum"), "olusma": d.get("olusma"), "kapak": (KOK / d["id"] / "kapak.jpg").exists(),
                    "degisti": p.stat().st_mtime, "yontem": y.get("yontem") or "", "yontem_baslik": y.get("baslik") or "",
                    "ozet": (y.get("ozet") or "")[:160]})
    return out


def istegi_degistir(cid, istek):
    return guncelle(cid, istek=istek.strip(), durum="planlaniyor")


def link_guvenli(link):
    """Yalnız herkese açık http(s) adresleri: yerel ağ ve bu bilgisayarın adreslerine istek gönderilmez (SSRF)."""
    import ipaddress
    import socket
    u = urlparse(link or "")
    h = u.hostname or ""
    if u.scheme not in ("http", "https") or not h or h.endswith(".local") or h == "localhost":
        return False
    try:
        for a in {x[4][0] for x in socket.getaddrinfo(h, None)}:
            ip = ipaddress.ip_address(a.split("%")[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
    except (OSError, ValueError):
        return False
    return True


def bos_alan_gb():
    try:
        return shutil.disk_usage(KOK if KOK.exists() else KLASOR).free / 1e9
    except Exception:  # noqa: BLE001
        return 99.0


def kapak_yap(video, hedef, sure):
    """Kapak: karanlık açılış karesi yerine ilk aydınlık kare (sürenin %8, %25, %45'i denenir)."""
    from PIL import Image, ImageStat
    for oran in (0.08, 0.25, 0.45):
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{max(0.3, sure * oran):.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=540:-2", str(hedef)], capture_output=True)
        try:
            if sum(ImageStat.Stat(Image.open(hedef).convert("L")).mean) > 28:
                return hedef
        except Exception:  # noqa: BLE001
            continue
    return hedef


def bilgi(video):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams") or [] if s.get("codec_type") == "video"), {})
    ses = any(s.get("codec_type") == "audio" for s in d.get("streams") or [])
    try:
        a, b = (v.get("r_frame_rate") or "30/1").split("/")
        fps = round(float(a) / float(b or 1), 2)
    except Exception:  # noqa: BLE001
        fps = 30.0
    return {"sure": float((d.get("format") or {}).get("duration") or 0), "w": int(v.get("width") or 0), "h": int(v.get("height") or 0),
            "fps": fps if 10 <= fps <= 61 else 30.0, "ses": ses}


def _indir(cid, link):
    """Video bir kez iner. İlk deneme oturumsuz; olmazsa ve Ayarlar'da bir tarayıcı seçildiyse o tarayıcının oturumuyla bir kez daha."""
    klasor = yol(cid)
    hedef = klasor / "kaynak.mp4"
    if hedef.exists() and hedef.stat().st_size > 10000:
        return hedef
    if not link_guvenli(link):
        raise RuntimeError("Bu link açılamıyor. Herkese açık bir video linki yapıştırın.")
    if re.search(r"tiktok\.com/@[^/]+/photo/\d+", link):          # TikTok fotoğraf gönderisi: yt-dlp desteklemiyor, sayfa verisinden
        log(cid, "Fotoğraf gönderisi indiriliyor")
        if _fotograflar(cid, link, hedef):
            return hedef
        raise RuntimeError("Bu fotoğraf gönderisi açılamadı; gizli olabilir.")
    log(cid, "Video indiriliyor")
    temel = [YTDLP, "--no-playlist", "--no-warnings", "-q", "-f", "bv*[height<=1920][ext=mp4]+ba[ext=m4a]/bv*[height<=1920]+ba/b",
             "--merge-output-format", "mp4", "--write-info-json", "--write-thumbnail", "--convert-thumbnails", "jpg",
             "-o", str(klasor / "kaynak.%(ext)s"), link]
    tarayici = ayar().get("tarayici")
    son = ""
    for ek in ([], ["--cookies-from-browser", tarayici]) if tarayici else ([],):
        r = subprocess.run(temel[:1] + ek + temel[1:], capture_output=True, text=True, timeout=900)
        if hedef.exists():
            break
        son = (r.stderr or "").strip()[-300:]
    if not hedef.exists():
        if "No video formats found" in son or "image" in son.lower():
            log(cid, "Bu gönderide video yok; fotoğraflar alınıyor")
            if _fotograflar(cid, link, hedef):                       # fotoğraf gönderisi (Instagram/TikTok): görseller slayt olarak aynı hattan geçer
                return hedef
            raise RuntimeError("Bu gönderide video yok ve fotoğrafları alınamadı. Gönderi gizli olabilir.")
        if re.search(r"private|login|log in|sign in|age", son, re.I):
            raise RuntimeError("Bu video gizli ya da yalnız giriş yapanlara açık; indirilemedi. Ayarlar'dan tarayıcı oturumunu açıp yeniden deneyin."
                               if not tarayici else "Bu video gizli ya da yalnız giriş yapanlara açık; indirilemedi.")
        if re.search(r"unavailable|removed|not found|404", son, re.I):
            raise RuntimeError("Bu video kaldırılmış ya da artık açılmıyor.")
        raise RuntimeError("Video indirilemedi. Linkin herkese açık bir videoya ait olduğundan emin olun.")
    return hedef


FOTO_SN = 3.0        # slaytta her görselin süresi


def _fotograflar(cid, link, hedef):
    """Fotoğraf gönderisi (TikTok photo, Instagram görsel): görseller `kaynak_foto/` klasörüne, sonra her biri FOTO_SN saniyelik sessiz bir slayt
    videosu (kaynak.mp4) olur ki kare, yazı ve karşılaştırma hattı değişmeden çalışsın. `statik.json` görsel listesini tutar. Döner: görsel sayısı."""
    import requests
    klasor = yol(cid)
    foto = klasor / "kaynak_foto"
    foto.mkdir(exist_ok=True)
    h = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
         "Accept-Language": "en-US,en;q=0.9"}
    urls, baslik, aciklama = [], "", ""
    try:
        t = requests.get(link, headers=h, timeout=25).text
    except Exception:  # noqa: BLE001
        t = ""
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', t, re.S)
    if m:                                                         # TikTok: imagePost.images[].imageURL.urlList
        try:
            scope = json.loads(m.group(1)).get("__DEFAULT_SCOPE__", {})
            it = (scope.get("webapp.video-detail") or scope.get("webapp.photo-detail") or {}).get("itemInfo", {}).get("itemStruct", {})
            for im in (it.get("imagePost") or {}).get("images") or []:
                u = ((im.get("imageURL") or {}).get("urlList") or [None])[0]
                if u:
                    urls.append(u)
            aciklama, baslik = it.get("desc") or "", (it.get("imagePost") or {}).get("title") or (it.get("desc") or "").split("\n")[0]
        except Exception:  # noqa: BLE001
            pass
    if not urls:                                                  # Instagram ve diğerleri: sayfadaki og:image'lar
        urls = [x for x in re.findall(r'property="og:image"\s+content="([^"]+)"', t)]
        mm = re.search(r'property="og:title"\s+content="([^"]*)"', t)
        baslik = baslik or (mm.group(1) if mm else "")
    if not urls and (klasor / "kaynak.jpg").exists():            # yt-dlp'nin yazdığı küçük resim
        urls = [str(klasor / "kaynak.jpg")]
    dosyalar = []
    for i, u in enumerate(urls[:12]):
        f = foto / f"f_{i:02d}.jpg"
        try:
            if u.startswith("http"):
                r = requests.get(u, headers={**h, "Referer": link}, timeout=30)
                if not r.ok or len(r.content) < 2000:
                    continue
                f.write_bytes(r.content)
            else:
                shutil.copy(u, f)
            from PIL import Image
            Image.open(f).convert("RGB").save(f, quality=90)   # webp/heic → jpg
            dosyalar.append(f)
        except Exception:  # noqa: BLE001
            continue
    if not dosyalar:
        return 0
    girdi = []
    for f in dosyalar:
        girdi += ["-loop", "1", "-t", str(FOTO_SN), "-i", str(f)]
    n = len(dosyalar)
    fc = "".join(f"[{i}:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=10[v{i}];" for i in range(n)) \
        + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    subprocess.run([FFMPEG, "-y", "-v", "error", *girdi, "-filter_complex", fc, "-map", "[v]", "-pix_fmt", "yuv420p", str(hedef)], capture_output=True, timeout=300)
    if not hedef.exists():
        return 0
    (klasor / "statik.json").write_text(json.dumps({"gorseller": [f.name for f in dosyalar], "baslik": baslik[:140], "aciklama": aciklama[:600], "sn": FOTO_SN},
                                                    ensure_ascii=False), encoding="utf-8")
    shutil.copy(dosyalar[0], klasor / "kapak.jpg")
    return n


def _kareler(video, sahneler, klasor, en_cok=40):
    """Her sahneden 1-3 kare; üstüne "Sahne N · t sn" yazılır (zamanlar yalnız metinde verilince model kareleri yanlış sayıyordu). [(sn, no, yol)]"""
    from PIL import Image, ImageDraw, ImageFont
    klasor.mkdir(parents=True, exist_ok=True)
    istek = []
    for s_ in sahneler:
        uz = s_["bit"] - s_["bas"]
        zz = [s_["bas"] + uz / 2] if uz < 1.2 else [s_["bas"] + 0.2, s_["bit"] - 0.2] if uz < 4 else [s_["bas"] + 0.2, s_["bas"] + uz / 2, s_["bit"] - 0.2]
        istek += [(round(t, 2), s_["no"]) for t in zz]
    if len(istek) > en_cok:
        istek = [istek[int(i * len(istek) / en_cok)] for i in range(en_cok)]
    try:
        yazi = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 26)
    except Exception:  # noqa: BLE001
        yazi = ImageFont.load_default()
    out = []
    for i, (t, no) in enumerate(istek):
        kyol = klasor / f"k_{i:03d}.jpg"
        if not kyol.exists():
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=480:-2",
                            "-q:v", "4", str(kyol)], capture_output=True)
            if kyol.exists():
                im = Image.open(kyol).convert("RGB")
                ImageDraw.Draw(im).rectangle([0, 0, im.width, 40], fill=(0, 0, 0))
                ImageDraw.Draw(im).text((10, 6), f"Sahne {no} · {t:.1f} sn", fill=(255, 220, 0), font=yazi)
                im.save(kyol, quality=85)
        if kyol.exists():
            out.append((t, no, kyol))
    return out


def _sahne_tespiti(video):
    """PySceneDetect (ayrı süreçte: OpenCV ile PyAV aynı süreçte çakışıyor); yoksa boş."""
    import csv
    import tempfile
    exe = KLASOR / ".venv" / "bin" / "scenedetect"
    exe = str(exe) if exe.exists() else shutil.which("scenedetect")
    if not exe:
        return []
    cikti = Path(tempfile.mkdtemp(prefix="sahne_"))
    try:
        subprocess.run([exe, "-q", "-i", str(video), "-o", str(cikti), "detect-adaptive", "list-scenes", "-q"], capture_output=True, text=True, timeout=600)
        csvler = list(cikti.glob("*.csv"))
        if not csvler:
            return []
        satirlar = list(csv.reader(csvler[0].read_text(encoding="utf-8").splitlines()[1:]))
        bas = satirlar[0].index("Start Time (seconds)")
        return [round(float(r[bas]), 2) for r in satirlar[2:] if len(r) > bas]
    except Exception:  # noqa: BLE001
        return []
    finally:
        shutil.rmtree(cikti, ignore_errors=True)


def _kesmeler(video):
    """PySceneDetect + ffmpeg sahne puanı (eşik 0,15) birleşimi, 0,3 sn'den yakın kesmeler tek (biri tek başına kısa/yumuşak kesmeleri kaçırıyor)."""
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", str(video), "-vf", "scale=160:-2,select='gt(scene,0.15)',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    hepsi = sorted(set(_sahne_tespiti(video)) | {round(float(x), 2) for x in re.findall(r"pts_time:([0-9.]+)", p.stderr)})
    out = []
    for k in hepsi:
        if not out or k - out[-1] > 0.3:
            out.append(k)
    return out


TARIF_ISTEM = """Bir viral kısa videoyu çözümlüyorsun. Amaç: bu videonun KALIBINI çıkarmak ki biri kendi versiyonunu yapabilsin.
Her karenin ÜSTÜNDE sarı yazıyla sahne numarası ve zamanı yazılı; sahne türünü o yazıya bakarak ver. Altta ses yazısı ve ekrandaki yazılar var.

Video: {baslik}
Açıklama: {aciklama}
Süre: {sure:.1f} sn, {w}x{h}
Sahneler (kesmelere göre): {sahneler}
Ses yazısı: {ses}
Ekran yazıları (OCR): {ocr}

Kare sayısı: {kare_listesi}

JSON döndür (Türkçe, sade, kısa):
{{
 "ozet": "videoda ne oluyor, 1-2 cümle",
 "neden_tutuyor": "şaka ya da çekim gücü, tek cümle",
 "sabit": "akımı akım yapan, kendi versiyonlarda DEĞİŞMEYEN kısım",
 "degisken": "insanların kendi versiyonunda değiştirdiği kısım",
 "yapay_zeka": true/false (görüntü yapay zekâ üretimi mi),
 "sahne_turleri": [{{"no": sahne no, "tur": "kaynak | ara | dis", "aciklama": "o sahnede ne var"}}],
 "kisiler": [{{"no": 1, "tarif": "kim/nasıl biri", "nerede": "solda / ortada / tek kişi", "kiyafet": "ne giyiyor"}}],
 "ses": "sesin ne olduğu (replik, müzik, ses efekti) ve kalıbın parçası mı",
 "kamera": "tek plan mı kesmeli mi; telefon gerçekçiliği mi sinematik mi",
 "ekran_yazisi_stili": "varsa: yer, renk, boyut"
}}
'kaynak' sahne = videonun asıl görüntüsü; 'ara' sahne = versiyonu yapanın kendi görüntüsünü koyduğu sahne; 'dis' sahne = akımın parçası
olmayan ek (nasıl yapılır anlatımı, uygulama ekranı, tanıtım, kapanış yazısı). Tek planlık videoda tek sahne vardır, türü 'kaynak'.
Kişileri yalnızca belirgin görünenlerle sınırla (seyirciler değil)."""


def _onceki_cozum(cid, link):
    """Aynı link daha önce çözüldüyse video ve kalıp yeniden indirilip çözülmez."""
    for p in sorted(KOK.glob("*/is.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.parent.name == cid:
            continue
        try:
            x = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if x.get("link") == link and x.get("tarif") and (p.parent / "kaynak.mp4").exists() and not x.get("test"):
            return x, p.parent
    return None, None


def cozumle(cid, planla_da=True):
    import claude_yaz
    d = oku(cid)
    klasor = yol(cid)
    if not (klasor / "kaynak.mp4").exists() and bos_alan_gb() < 3:
        raise RuntimeError(f"Diskte {bos_alan_gb():.1f} GB boş yer kaldı; video indirilmedi. Birkaç GB yer açıp yeniden deneyin.")
    if not d.get("tarif") and not (klasor / "kaynak.mp4").exists() and not d.get("kanit_sakla"):
        x, k = _onceki_cozum(cid, d["link"])
        if x:
            log(cid, "Bu video daha önce çözülmüş; hazır çözüm kullanılıyor")
            for f in ("kaynak.mp4", "kapak.jpg"):
                if (k / f).exists():
                    shutil.copy(k / f, klasor / f)
            for f in k.glob("kaynak*.info.json"):
                shutil.copy(f, klasor / f.name)
            if (k / "kareler").exists():
                shutil.copytree(k / "kareler", klasor / "kareler", dirs_exist_ok=True)
            guncelle(cid, tarif=x["tarif"], kaynak=x.get("kaynak") or {}, onceki_is=x["id"])
            if planla_da:
                import content_yontem
                content_yontem.coz(cid)
            return
    video = _indir(cid, d["link"])
    b = bilgi(video)
    inf = {}
    try:
        inf = json.loads(next(klasor.glob("kaynak*.info.json")).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    if not (klasor / "kapak.jpg").exists():
        kapak_yap(video, klasor / "kapak.jpg", b["sure"])
    if d.get("kanit_sakla"):     # deneme: sahibin/platformun söylediği gizlenir; yöntem yalnız videodan bulunmalı (content_test)
        inf = {k: v for k, v in inf.items() if k not in ("description", "title", "tags", "fulltitle", "uploader", "channel", "uploader_id", "channel_id")}
    statik = {}
    try:
        statik = json.loads((klasor / "statik.json").read_text(encoding="utf-8"))     # fotoğraf gönderisi: görseller slayt olarak işlenir
    except Exception:  # noqa: BLE001
        pass
    if statik and not d.get("kanit_sakla"):
        inf = {**inf, "title": statik.get("baslik") or inf.get("title"), "description": statik.get("aciklama") or inf.get("description")}
    kaynak = {"baslik": (inf.get("description") or inf.get("title") or "").split("\n")[0][:140] or ("(gizli)" if d.get("kanit_sakla") else Path(d["link"]).name),
              "kanal": inf.get("uploader") or inf.get("channel") or "", "aciklama": (inf.get("description") or "")[:600],
              "begeni": inf.get("like_count"), "izlenme": inf.get("view_count"), **b,
              **({"statik": len(statik.get("gorseller") or []), "statik_sn": statik.get("sn") or FOTO_SN} if statik else {})}
    guncelle(cid, kaynak=kaynak)

    if not d.get("tarif"):
        log(cid, "Ses yazıya dökülüyor")
        ses = {"metin": ""}
        if b["ses"]:
            try:
                ses = json.loads(subprocess.run([PYTHON, str(KLASOR / "sesnot.py"), str(video), ""], capture_output=True, text=True,
                                                timeout=600).stdout or "{}")
            except Exception:  # noqa: BLE001
                pass
        log(cid, "Sahneler ayrılıyor")
        if kaynak.get("statik"):                                 # her görsel bir sahne; sahne tespiti gereksiz
            kesim = [round(i * kaynak["statik_sn"], 2) for i in range(1, kaynak["statik"])]
        else:
            kesim = [k for k in _kesmeler(video) if 0.3 < k < b["sure"] - 0.3]
        sinirlar = [0.0] + kesim + [b["sure"]]
        sahneler = [{"no": i + 1, "bas": round(sinirlar[i], 2), "bit": round(sinirlar[i + 1], 2)} for i in range(len(sinirlar) - 1)]
        log(cid, "Kareler inceleniyor")
        shutil.rmtree(klasor / "kareler", ignore_errors=True)
        kareler = _kareler(video, sahneler, klasor / "kareler")
        import goruntu
        ocr = []
        for t, _, kyol in kareler:
            try:
                y = [s for s in goruntu.yazi_oku(kyol) if len(s.strip()) > 1]
            except Exception:  # noqa: BLE001
                y = []
            if y and (not ocr or ocr[-1][1] != y):
                ocr.append((t, y))
        istem = TARIF_ISTEM.format(
            baslik=kaynak["baslik"], aciklama=kaynak["aciklama"][:400] or "-", sure=b["sure"], w=b["w"], h=b["h"],
            sahneler=", ".join(f"{s['no']}: {s['bas']:.1f}-{s['bit']:.1f} sn" for s in sahneler),
            ses=(ses.get("metin") or "(konuşma yok)")[:1500],
            ocr="; ".join(f"{t:.1f} sn: {' / '.join(y)}" for t, y in ocr)[:1200] or "(yok)",
            kare_listesi=f"{len(kareler)}, {len(sahneler)} sahneden")
        log(cid, "Videonun kalıbı çıkarılıyor")
        tarif = claude_yaz.json_coz(claude_yaz.sor_gorsel(istem, [y for _, _, y in kareler], model_adi="sonnet"))
        if not tarif:
            raise RuntimeError("Video çözümlenemedi (yanıt okunamadı).")
        turler = {int(x.get("no") or 0): x for x in tarif.get("sahne_turleri") or []}
        for s in sahneler:
            x = turler.get(s["no"]) or {}
            s["tur"] = x.get("tur") if x.get("tur") in ("ara", "dis") else "kaynak"
            s["aciklama"] = x.get("aciklama") or ""
        tarif["sahneler"] = sahneler
        tarif["ses_yazisi"] = ses.get("metin") or ""
        tarif["yazilar"] = [{"sn": t, "metin": " / ".join(y)} for t, y in ocr]
        guncelle(cid, tarif=tarif)
    if planla_da:
        import content_yontem
        content_yontem.coz(cid)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "coz":
        c = yeni(a[1], a[2] if len(a) > 2 else "")
        cozumle(c)
        print(json.dumps((oku(c) or {}).get("yontem") or {}, ensure_ascii=False, indent=1))
    else:
        print(__doc__)
