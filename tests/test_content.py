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
