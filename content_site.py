"""content_site.py - Content'in uçları (2026-10-23; 2026-10-29 sade sürüm). `content_site.kaydet(app)` ile herhangi bir Flask uygulamasına bağlanır:
Video Hub'ın ortak sunucusu (site.py, port 8769) ya da tek başına `content_sunucu.py`. Sayfa static/content.html.

İşler iş parçacığıyla çalışır; durum content/<id>/is.json'da. Sunucu yeniden başlarsa yarım iş "kesildi" olur, "Tekrar dene" kaldığı yerden sürer.
"""
import re
import threading
import time
import traceback

from flask import abort, jsonify, request, send_from_directory

import content

calisan = {}                      # cid -> aşama
_kilit = threading.Lock()


def mesgul():
    """Yeniden başlatma bunları bekler."""
    return [f"Content: {a}" for a in list(calisan.values())]


def _arka(cid, asama, is_, *arg):
    def kos():
        try:
            is_(*arg)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            content.guncelle(cid, durum="hata", hata=(str(e) or type(e).__name__)[:400], hata_asama=asama)
        finally:
            with _kilit:
                calisan.pop(cid, None)
    with _kilit:
        if cid in calisan:
            return False
        calisan[cid] = asama
    threading.Thread(target=kos, daemon=True).start()
    return True


def _bildir(metin, baslik="Content"):
    try:
        import subprocess
        tr = lambda s: str(s).replace("\\", " ").replace('"', " ").replace("\n", " ")[:220]   # AppleScript kaçış dizilerini tanımıyor
        subprocess.Popen(["/usr/bin/osascript", "-e", f'display notification "{tr(metin)}" with title "{tr(baslik)}"'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:  # noqa: BLE001
        pass


def _bitti_mesaji(cid):
    return "How it was made is ready." if (content.oku(cid) or {}).get("dil") == "en" else "Videonun nasıl yapıldığı çözüldü; adım adım rehber hazır."


def _cozumle(cid):
    content.guncelle(cid, durum="cozuluyor", hata="")
    content.cozumle(cid)
    _bildir(_bitti_mesaji(cid))


def _planla(cid):
    import content_yontem
    content.guncelle(cid, durum="planlaniyor", hata="")
    content_yontem.coz(cid)
    _bildir(_bitti_mesaji(cid))


def _kesilenleri_isaretle():
    """Açılışta: süreç içinde yarım kalanlar kesildi olarak görünür."""
    for p in content.KOK.glob("*/is.json"):
        cid = p.parent.name
        try:
            d = content.oku(cid) or {}
        except ValueError:
            continue
        if d.get("durum") in ("cozuluyor", "planlaniyor") and cid not in calisan and not d.get("test"):   # denemeler ayrı süreçte çalışır
            try:
                content.guncelle(cid, durum="kesildi", onceki_durum=d["durum"], adim="Yarıda kaldı", hata="İnceleme yarıda kaldı.")
            except ValueError:
                pass


def _dis(d):
    d = {k: v for k, v in d.items() if k not in ("bulut_istekleri", "bulut_dosyalari", "kare_notlari", "yorumlar")}
    d["log"] = (d.get("log") or [])[-8:]
    if d.get("tarif"):
        d["tarif"] = {k: v for k, v in d["tarif"].items() if k != "ses_yazisi"}
    d["calisiyor"] = d["id"] in calisan
    d["kapak"] = (content.KOK / d["id"] / "kapak.jpg").exists()       # sayfa, kapağı olmayan (indirilememiş) video için boş kutu çizmesin
    return d


def _dil(v):
    x = str((v or {}).get("dil") or content.ayar().get("dil") or "")
    return x if x in ("tr", "en") else "tr"


def kaydet(app):
    content.KOK.mkdir(parents=True, exist_ok=True)
    _kesilenleri_isaretle()

    @app.get("/api/content")
    def content_liste():
        return jsonify({"isler": content.liste(), "ayar": content.ayar()})

    @app.post("/api/content")
    def content_yeni():
        v = request.get_json(silent=True) or {}
        link = str(v.get("link") or "").strip()
        if not re.match(r"^https?://\S+$", link) or not content.link_guvenli(link):
            return jsonify({"hata": "Geçerli, herkese açık bir video linki yapıştırın."}), 400
        cid = content.yeni(link, str(v.get("istek") or "")[:1500], dil=_dil(v))
        _arka(cid, "çözümleme", _cozumle, cid)
        return jsonify({"id": cid})

    @app.get("/api/content/<cid>")
    def content_oku(cid):
        try:
            d = content.oku(cid)
        except ValueError:
            abort(404)
        if not d or d.get("silindi"):
            abort(404)
        return jsonify(_dis(d))

    @app.post("/api/content/<cid>/istek")
    def content_istek(cid):
        d = content.oku(cid) or {}
        if not d:
            abort(404)
        v = request.get_json(silent=True) or {}
        content.istegi_degistir(cid, str(v.get("istek") or "").strip()[:1500])
        if v.get("dil") in ("tr", "en"):
            content.guncelle(cid, dil=v["dil"])
        ok = _arka(cid, "plan", _planla, cid) if d.get("tarif") else _arka(cid, "çözümleme", _cozumle, cid)
        return (jsonify({"ok": True}) if ok else (jsonify({"hata": "Bu video şu an inceleniyor."}), 409))

    @app.post("/api/content/<cid>/yontem")
    def content_yontem_uc(cid):
        d = content.oku(cid) or {}
        if not d:
            abort(404)
        v = request.get_json(silent=True) or {}
        if v.get("dil") in ("tr", "en"):
            content.guncelle(cid, dil=v["dil"])
        ok = _arka(cid, "plan", _planla, cid) if d.get("tarif") else _arka(cid, "çözümleme", _cozumle, cid)
        return (jsonify({"ok": True}) if ok else (jsonify({"hata": "Bu video şu an inceleniyor."}), 409))

    @app.post("/api/content/<cid>/dogru")
    def content_dogru(cid):
        """"Doğru mu?" cevabı: düzeltme varsa rehber onunla yeniden yazılır; ders ve deneme kaydı content_dogrulama'da."""
        import content_dogrulama
        v = request.get_json(silent=True) or {}
        karar, not_ = str(v.get("karar") or ""), str(v.get("not") or "").strip()[:1200]
        d = content.oku(cid) or {}
        if karar not in content_dogrulama.KARARLAR or not d.get("yontem"):
            return jsonify({"hata": "Geçersiz istek."}), 400
        if karar != "dogru" and not not_:
            return jsonify({"hata": "Videonun aslında nasıl yapıldığını kısaca yazın."}), 400
        if karar == "dogru":
            threading.Thread(target=lambda: content_dogrulama.kaydet(cid, karar), daemon=True).start()
            content.guncelle(cid, dogrulama={"karar": "dogru", "t": time.time()})
            return jsonify({"ok": True})

        def duzelt():
            content.log(cid, "Düzeltmeniz işleniyor")
            content_dogrulama.kaydet(cid, karar, not_)
            _planla(cid)
        if not _arka(cid, "plan", duzelt):
            return jsonify({"hata": "Bu video şu an inceleniyor; bitince yeniden deneyin."}), 409
        return jsonify({"ok": True})

    @app.delete("/api/content/<cid>")
    def content_sil(cid):
        if cid in calisan:
            return jsonify({"hata": "Bu video şu an inceleniyor; bitince silebilirsiniz."}), 409
        if not content.oku(cid):
            abort(404)
        content.guncelle(cid, silindi=time.time())
        return jsonify({"ok": True})

    @app.post("/api/content/<cid>/geri-al")
    def content_geri_al(cid):
        if not content.oku(cid):
            abort(404)
        content.degistir(cid, lambda d: d.pop("silindi", None))
        return jsonify({"ok": True})

    @app.get("/api/content/ayar")
    def content_ayar_oku():
        import importlib.util
        return jsonify({**content.ayar(), "shazam_kurulu": importlib.util.find_spec("shazamio") is not None})

    @app.post("/api/content/ayar")
    def content_ayar_yaz():
        return jsonify(content.ayar_yaz(request.get_json(silent=True) or {}))

    @app.get("/content-dosya/<cid>/<path:yol>")
    def content_dosya(cid, yol):
        try:
            kok = content.yol(cid)
        except ValueError:
            abort(404)
        if ".." in yol or not re.fullmatch(r"kaynak\.mp4|kapak\.jpg|kareler/k_\d+\.jpg", yol) or not (kok / yol).exists():
            abort(404)
        return send_from_directory(str(kok), yol, max_age=3600)
