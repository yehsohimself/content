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
    uzun = A.olc({"kaynak": {"w": 1080, "h": 1920, "fps": 30, "sure": 38}, "tarif": {"sahneler": [{"bas": 0, "bit": 34}, {"bas": 34, "bit": 38}]}})
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


def test_sohbet_yaniti_ayrilir_ve_bos_mesaj_reddedilir(istemci, kok):
    import content_sohbet
    metin, sec, ey = content_sohbet.ayir('Olur.\n@@ {"secenekler": ["Telefonda", "Bilgisayarda"], "eylem": {"tur": "yeniden", "istek": "Telefonda yapacağım", "etiket": "Telefona göre yaz"}}')
    assert metin == "Olur." and sec == ["Telefonda", "Bilgisayarda"] and ey["tur"] == "yeniden" and ey["istek"]
    assert content_sohbet.ayir('Bilmiyorum.\n@@ {"eylem": {"tur": "sil"}}')[2] is None        # bilinmeyen eylem atılır
    assert content_sohbet.ayir("Düz yanıt")[0] == "Düz yanıt"
    cid = _sahte_is(kok, "abcdef0123")
    assert istemci.post(f"/api/content/{cid}/sohbet", json={"mesaj": " "}).status_code == 400
    assert istemci.post("/api/content/sohbet", json={}).status_code == 400
    assert istemci.delete(f"/api/content/{cid}/sohbet").status_code == 200


def _sahte_olcum():
    return {"source": {"duration": 20.0},
            "shots": [{"id": "shot_001", "index": 1, "start": 0.0, "end": 8.0, "duration": 8.0, "base": {"label": "ai_video", "confidence": .7}, "deterministic": {"probs": {"ai_video": .7, "live_action": .3}}, "review": {"raw_probs": {"live_action": .9, "ai_video": .1}, "replication": {"video_prompt_en": "gereksiz"}}, "assets": {"sheet": "shots/shot_001.jpg"}},
                      {"id": "shot_002", "index": 2, "start": 8.0, "end": 20.0, "duration": 12.0, "base": {"label": "live_action", "confidence": .55}, "deterministic": {"probs": {"live_action": .6, "ai_video": .4}}, "assets": {"sheet": "shots/shot_002.jpg"},
                       "review": {"raw_probs": {"ai_video": .55, "live_action": .45}, "ai_edits": [{"kind": "lip_sync", "evidence": "ağız"}], "replication": {"video_prompt_en": "a dog runs"}}}],
            "audio": {"has_audio": True, "voice": {"present": True}, "music": {"present": True, "tempo_bpm": 120.0, "beat_strength": .2, "key": {"tonic": "C", "mode": "minor", "confidence": .3}}, "sfx": {}},
            "sound_sources": {"music": {"probs": {"popular_song": .7, "ai_generated": .3}}},
            "packaging": {"text_cues": [{"t0": 1, "text": "三", "kind": "label"}, {"t0": 2, "text": "中文字幕", "kind": "subtitle"}, {"t0": 3, "text": "Hello world", "kind": "subtitle"}], "stickers": []},
            "provenance": {"aigc": {"label": ""}, "hints": {"generator": ["Google Veo?"], "editor": ["CapCut/剪映"]}, "evidence": []},
            "video_context": {"transcoded": True}, "production_plan": {"units": [], "calls": 0}, "summary": {"avg_shot_s": 10}}


def test_olcum_cop_ve_zayif_izi_almaz(istemci):
    """Çince tanıma çöpü, tek harf ve dosyada rastgele geçen 'veo' kanıt olmaz; güveni düşük anahtar yazılmaz."""
    import content_olcum as O
    cid = _sahte_is(None)
    o = O.ozet(cid, _sahte_olcum())
    assert o["yazi"]["altyazi"] == 1 and o["yazi"]["etiket"] == 0
    assert o["izler"]["uretici"] == [] and o["izler"]["duzenleyici"] == ["CapCut/剪映"] and o["izler"]["yapay_zeka_etiketi"] is False
    assert o["ses"]["muzik"]["bpm"] == 120.0 and o["ses"]["muzik"]["anahtar"] is None
    assert [round(x["oran"], 1) for x in o["karisim"]] == [.6, .4] and o["karisim"][0]["tur"] == "ai_video"
    s = o["sahneler"][1]
    assert o["sahneler"][0]["tur"] == "live_action" and o["sahneler"][0]["istem_en"] == ""     # gerçek çekimde göz ölçümü geçer, istem yazılmaz
    assert s["supheli"] and s["istem_en"] == "a dog runs" and s["ikinci"] == "Gerçek çekim" and s["islem"][0]["ad"] == "dudak uyumu yapılmış"
    m = O.istem_metni(o)
    assert "no 2, 8.0-20.0 sn: Yapay zekâ videosu" in m and "emin değil" in m and "Veo" not in m


def test_ana_inceleme_cekimi_duzeltir(istemci):
    import content
    import content_olcum as O
    cid = _sahte_is(None)
    content.guncelle(cid, olcum=O.ozet(cid, _sahte_olcum()))
    O.karar_uygula(cid, {"cekim_karari": [{"no": 2, "tur": "live_action", "neden": "yayıncı kamera arkasını paylaşmış", "guven": "yuksek"}, {"no": 9, "tur": "ai_video"}, {"no": 1, "tur": "uydurma"}]})
    o = content.oku(cid)["olcum"]
    s = o["sahneler"][1]
    assert s["tur"] == "live_action" and s["ad"] == "Gerçek çekim" and not s["supheli"] and s["istem_en"] == "" and s["kanit"][0].startswith("yayıncı")
    assert o["karisim"] == [{"tur": "live_action", "ad": "Gerçek çekim", "oran": 1.0}]


def test_olcum_arac_yoksa_sessizce_gecer(istemci, monkeypatch):
    import content_olcum as O
    monkeypatch.setattr(O, "REA_PY", O.KLASOR / "yok" / "python")
    assert O.hazir() is False and O.calistir(_sahte_is(None), log=lambda m: None) is None
    assert O.istem_metni(None).startswith("(sahne")


def test_ayrilmis_ses_yolu_yalniz_izinli_dosyalar(istemci):
    import content
    cid = _sahte_is(None)
    k = content.yol(cid) / "is_ara" / "rea"
    (k / "stems").mkdir(parents=True)
    (k / "stems" / "music.m4a").write_bytes(b"x")
    (k / "breakdown.json").write_text("{}")
    assert istemci.get(f"/content-dosya/{cid}/is_ara/rea/stems/music.m4a").status_code == 200
    assert istemci.get(f"/content-dosya/{cid}/is_ara/rea/breakdown.json").status_code == 404


def test_olculen_tur_goze_ezilmez():
    import content_olcum as O
    s = {"deterministic": {"probs": {"static_hold": .9, "ai_video": .1}}, "review": {"raw_probs": {"ai_video": 1}}}
    assert O._karar(s)[0] == "static_hold"
    s = {"deterministic": {"probs": {"ai_video": .8}}, "base": {"label": "ai_video", "confidence": .8}}      # bakılmamış: güven düşük, emin değil
    k = O._karar(s)
    assert k[0] == "ai_video" and k[1] <= .55 and k[3] is True


def test_kendi_kare_etiketimiz_yazi_sayilmaz():
    import content
    t = {"yazilar": [{"sn": 0.2, "metin": "Sahne 1 • 0.2 sn"}, {"sn": 1, "metin": "POV: / Sahne 2 · 1.6 sn"}, {"sn": 2, "metin": "S3 · 2.4s"}]}
    assert content.gercek_yazilar(t) == [{"sn": 1, "metin": "POV:"}]


def test_akim_kanallari_ve_kalip():
    import content_akim as A
    i = A._temiz({"goruntu": {"ne": "konuşan böcek", "aramalar": ["talking cockroach AI video", "hamam"]}, "konusma": {"ne": "", "aramalar": []}, "en_guclu": "hareket"})
    assert list(i) == ["goruntu", "en_guclu"] and i["en_guclu"] == "goruntu" and i["goruntu"]["aramalar"] == ["talking cockroach AI video"]   # kısa tek sözcük arama olamaz
    assert A.aramalar(i) == ["talking cockroach AI video"]
    assert A._numarasiz("Konuşan böcek (bu videoyla birlikte 1, 2 ve 3'te görüldü).") == "Konuşan böcek."
    assert A._numarasiz("milli takım forması (1), beyaz tişört (2 ve 3).") == "milli takım forması, beyaz tişört."
    assert A._numarasiz("3 kişi (iki kadın) var") == "3 kişi (iki kadın) var"
    assert "bilinmiyor" in A.kalip_metni({}) and "SABİT: x" in A.kalip_metni({"ornekler": [{}], "sabit": ["x"], "bazen": [], "degisen": [], "kollar": [], "emin": "orta"})
    assert A.kanal_temizle({"kanallar": [{"kanal": "uydurma", "bulgu": "a"}, {"kanal": "ses", "bulgu": "b", "link": "javascript:x"}]}) == [{"kanal": "ses", "ad": "Ses", "bulgu": "b", "link": ""}]


def test_tek_sozcuk_oneri_aramaya_girmez(monkeypatch):
    import content_benzer as B
    goren = []
    monkeypatch.setattr(B, "_ara", lambda q, g: goren.append(q) or [])
    B.adaylar({"akim_imza": {"goruntu": {"ne": "x", "aramalar": ["talking cockroach AI video"]}, "en_guclu": "goruntu"}}, sayfa={"tiktok_onerilen_aramalar": ["hamam", "hamam böceği"]})
    assert "hamam #shorts" not in goren and "hamam böceği #shorts" in goren and goren[0].startswith("talking cockroach")
