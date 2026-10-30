"""Content: the server, its safety checks, settings and the evidence rules. No video is downloaded and no Claude call is made."""
import json


def test_ana_sayfa(istemci):
    r = istemci.get("/")
    assert r.status_code == 200 and b'data-urunler="content"' in r.data


def test_liste_bos(istemci):
    j = istemci.get("/api/content").get_json()
    assert j["isler"] == [] and j["ayar"]["shazam"] is False and j["ayar"]["yorumlar"] is False and j["ayar"]["sunra"] is True


def test_yerel_adres_reddedilir(istemci):
    for link in ("http://127.0.0.1:8765/api/ayarlar", "http://localhost/x", "http://192.168.1.10/video.mp4", "http://169.254.169.254/latest",
                 "file:///etc/passwd", "/tmp/video.mp4", "ftp://example.com/a.mp4", "http://drucker.local/a"):
        r = istemci.post("/api/content", json={"link": link})
        assert r.status_code == 400, link
    import content
    assert content.liste() == []


def test_link_guvenli():
    import content
    assert not content.link_guvenli("http://10.0.0.5/a.mp4")
    assert not content.link_guvenli("javascript:alert(1)")
    assert not content.link_guvenli("")


def test_ayarlar_yalniz_bilinen_degerler(istemci):
    j = istemci.post("/api/content/ayar", json={"shazam": 1, "tarayici": "rm -rf /", "dil": "de", "yabanci": True}).get_json()
    assert j["shazam"] is True and j["tarayici"] == "" and j["dil"] == "" and "yabanci" not in j
    j = istemci.post("/api/content/ayar", json={"shazam": False, "tarayici": "chrome", "dil": "en"}).get_json()
    assert j["shazam"] is False and j["tarayici"] == "chrome" and j["dil"] == "en"
    istemci.post("/api/content/ayar", json={"tarayici": "", "dil": ""})


def _sahte_is(kok, cid="abcdef0123"):
    import content
    (content.KOK / cid / "kareler").mkdir(parents=True, exist_ok=True)
    (content.KOK / cid / "kapak.jpg").write_bytes(b"\xff\xd8\xff")
    (content.KOK / cid / "kareler" / "k_000.jpg").write_bytes(b"\xff\xd8\xff")
    (content.KOK / cid / "gizli.txt").write_text("x")
    content.yaz(cid, {"id": cid, "link": "https://example.com/v", "istek": "", "durum": "yontem", "log": [],
                      "yontem": {"yontem": "capcut_sablon", "baslik": "Hazır şablon", "ozet": "…", "adimlar": [{"baslik": "a"}]}})
    return cid


def test_dosya_yolu_suzgeci(istemci, kok):
    cid = _sahte_is(kok)
    assert istemci.get(f"/content-dosya/{cid}/kapak.jpg").status_code == 200
    assert istemci.get(f"/content-dosya/{cid}/kareler/k_000.jpg").status_code == 200
    for yol in ("is.json", "gizli.txt", "../ayarlar.json", "kareler/../is.json", "kaynak.info.json"):
        assert istemci.get(f"/content-dosya/{cid}/{yol}").status_code == 404, yol
    assert istemci.get("/content-dosya/../x/kapak.jpg").status_code == 404


def test_oku_sil_geri_al(istemci, kok):
    cid = _sahte_is(kok, "0123456789")
    d = istemci.get(f"/api/content/{cid}").get_json()
    assert d["yontem"]["baslik"] == "Hazır şablon" and d["calisiyor"] is False
    assert istemci.delete(f"/api/content/{cid}").status_code == 200
    assert istemci.get(f"/api/content/{cid}").status_code == 404
    assert istemci.post(f"/api/content/{cid}/geri-al").status_code == 200
    assert istemci.get(f"/api/content/{cid}").status_code == 200
    assert istemci.get("/api/content/xyz").status_code == 404


def test_dogru_mu_dogrulama(istemci, kok):
    cid = _sahte_is(kok, "fedcba9876")
    assert istemci.post(f"/api/content/{cid}/dogru", json={"karar": "belki"}).status_code == 400
    assert istemci.post(f"/api/content/{cid}/dogru", json={"karar": "yanlis"}).status_code == 400      # düzeltme metni şart


def test_yabanci_kokenden_yazma_reddedilir(istemci):
    r = istemci.post("/api/content", json={"link": "https://www.tiktok.com/@a/video/1"}, headers={"Origin": "https://kotu.example"})
    assert r.status_code == 403


def test_kanit_kademesi():
    import content_kanit as K
    y = {"guven": "yuksek", "araclar": [{"ad": "Kling", "dayanak": "gorsel"}, {"ad": "CapCut", "dayanak": "reklam"}]}
    y = K.kademe(y, {}, {}, [], {})
    assert y["kademe"] in ("olası", "güçlü olasılık", "bilinmiyor") and y["guven"] != "yuksek"
    y = K.kademe({"guven": "yuksek", "araclar": [{"ad": "CapCut", "dayanak": "platform"}]}, {"baglantilar": [{"sablon_id": "1"}]}, {}, [], {})
    assert y["kademe"] == "kesin"


def test_arac_izleri():
    import content_araclar as A
    d = {"kaynak": {"w": 1280, "h": 704, "fps": 30, "sure": 24},
         "tarif": {"sahneler": [{"bas": 0, "bit": 8.0}, {"bas": 8.0, "bit": 16.0}, {"bas": 16.0, "bit": 24.0}]}}
    m = "\n".join(A.olc(d))
    assert "Sora 2" in m and "8 sn" in m
    assert "Veo" in A.defter_metni()
    uzun = A.olc({"kaynak": {"w": 1080, "h": 1920, "fps": 30, "sure": 31}, "tarif": {"sahneler": [{"bas": 0, "bit": 27}, {"bas": 27, "bit": 31}]}})
    assert any("kesmesiz" in x for x in uzun)


def test_ses_benzerligi_ve_kayma():
    import numpy as np
    import content_benzer as B
    rng = np.random.default_rng(3)
    a = rng.standard_normal(20 * 30)                       # 30 sn zarf
    b = np.concatenate([rng.standard_normal(20 * 2), a[: 20 * 20]])   # aynı ses, 2 sn geç başlıyor, 20 sn
    s, kayma = B.ses_benzerligi(a, b)
    assert s > 0.95 and abs(kayma) == 2.0
    s2, _ = B.ses_benzerligi(a, rng.standard_normal(20 * 20))
    assert s2 < 0.35
    assert B.ses_benzerligi(None, a) == (0.0, 0.0)


def test_gorsel_benzerligi_ve_serit(tmp_path):
    from PIL import Image, ImageDraw
    import content_benzer as B
    a, b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    im = Image.new("RGB", (320, 560), (30, 60, 200)); ImageDraw.Draw(im).ellipse([80, 120, 240, 420], fill=(240, 220, 90)); im.save(a)
    im2 = Image.new("RGB", (320, 560), (250, 250, 250)); ImageDraw.Draw(im2).rectangle([20, 20, 120, 80], fill=(0, 0, 0)); im2.save(b)
    ayni, _ = B.gorsel_benzerligi([a], [a])
    farkli, _ = B.gorsel_benzerligi([a], [b])
    assert ayni > 0.99 and farkli < 0.8
    s = B.serit([a, a], [b, b], tmp_path / "serit.jpg")
    assert s and s.exists() and Image.open(s).size[0] == 360
    assert "ses aynı" in B.yorum(0.9, 0.3, 0.3) and "görüntü aynı" in B.yorum(0.1, 0.95, 0.99)
    assert "(benzer video bulunamadı)" == B.istem_metni([])


def test_fotograf_gonderisi_slayt_olur(kok, tmp_path):
    """Fotoğraf gönderisi: görseller (burada yerel dosya) slayt videosu + statik.json olur; sahneler görsel başına."""
    from PIL import Image
    import content
    f1, f2 = tmp_path / "x1.jpg", tmp_path / "x2.jpg"
    Image.new("RGB", (600, 800), (200, 30, 30)).save(f1); Image.new("RGB", (800, 600), (30, 200, 30)).save(f2)
    cid = content.yeni("https://www.tiktok.com/@a/photo/7000000000000000001", "")
    import unittest.mock as um
    class Sahte:
        text = ""
        def __init__(self, *a, **k): pass
    with um.patch("requests.get", return_value=Sahte()):
        # sayfa okunamadı → og:image yok → yt-dlp küçük resmi de yok → yerel dosyalar verilemez; bu yüzden dosyaları doğrudan kaynak.jpg yoluyla veriyoruz
        import shutil
        shutil.copy(f1, content.yol(cid) / "kaynak.jpg")
        n = content._fotograflar(cid, "https://www.tiktok.com/@a/photo/7000000000000000001", content.yol(cid) / "kaynak.mp4")
    assert n == 1 and (content.yol(cid) / "kaynak.mp4").exists() and (content.yol(cid) / "kapak.jpg").exists()
    st = json.loads((content.yol(cid) / "statik.json").read_text(encoding="utf-8"))
    assert st["gorseller"] == ["f_00.jpg"] and st["sn"] == content.FOTO_SN
    b = content.bilgi(content.yol(cid) / "kaynak.mp4")
    assert abs(b["sure"] - content.FOTO_SN) < 0.6 and b["w"] == 720 and b["h"] == 1280 and not b["ses"]


def test_tiktok_fotograf_sayfasi_ayristirilir(kok, tmp_path):
    """TikTok fotoğraf sayfasının gömülü verisinden görseller alınır (yerel sunucu yerine sahte yanıt)."""
    from PIL import Image
    import content
    import unittest.mock as um
    g = tmp_path / "g.jpg"; Image.new("RGB", (400, 700), (10, 10, 120)).save(g)
    veri = {"__DEFAULT_SCOPE__": {"webapp.video-detail": {"itemInfo": {"itemStruct": {"desc": "deneme #ai", "imagePost": {"title": "Kolaj",
            "images": [{"imageURL": {"urlList": ["http://ornek.test/1.jpg"]}}, {"imageURL": {"urlList": ["http://ornek.test/2.jpg"]}}]}}}}}}
    sayfa = f'<html><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">{json.dumps(veri)}</script></html>'
    class Yanit:
        def __init__(self, url):
            self.ok, self.text, self.content = True, sayfa, g.read_bytes()
    cid = content.yeni("https://www.tiktok.com/@a/photo/7000000000000000002", "")
    with um.patch("requests.get", side_effect=lambda url, **k: Yanit(url)):
        n = content._fotograflar(cid, "https://www.tiktok.com/@a/photo/7000000000000000002", content.yol(cid) / "kaynak.mp4")
    assert n == 2
    st = json.loads((content.yol(cid) / "statik.json").read_text(encoding="utf-8"))
    assert st["baslik"] == "Kolaj" and st["aciklama"] == "deneme #ai" and len(st["gorseller"]) == 2
    assert abs(content.bilgi(content.yol(cid) / "kaynak.mp4")["sure"] - 2 * content.FOTO_SN) < 0.6
