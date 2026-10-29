"""content_test.py - "nasıl yapılmış" çözümlemesinin cevabı bilinen videolarla sınanması (2026-10-29).

Test seti `content/test_seti.json` (veri klasörü, git dışı). Her kayıt:
  {"ad": "...", "beklenen": {"yontem": [...], "kaynak_klip": [...], "arac": [...], "ozet": [...]},
   "kaynak_id": "<kullanıcının Content işi>"   ya da   "link": "<video>", "sakla": true, "kaynak": "kim etiketledi"}
Beklenen alanlarda listedeki sözcüklerin HEPSİ ilgili metinde geçmeli; "a|b" = a ya da b; yontem: listedekilerden BİRİ.
Her deneme gizli bir kopya iş üzerinde çalışır (`test: true`; listede görünmez): kullanıcının işi ve düzeltmesi değişmez, düzeltme cevaba
sızmaz, dersin kendi videosu deneme sırasında istemden çıkarılır. `sakla`: başlık, açıklama, etiketler, platform sayfası, yorumlar ve dosya
etiketi gizlenir; sahibin ya da platformun söylediği bilinmeden yöntem yalnız videodan bulunmalı. Sonuç `content/test_sonuclari.jsonl`.

Elle: python content_test.py [--kutuphanesiz] [--yeni] [sıra no | ad parçası ...]
  --kutuphanesiz: kütüphanedeki eski çözümler kullanılmaz.  --yeni: yalnız hiç denenmemiş kayıtlar.
"""
import json
import shutil
import sys
import time
import unicodedata

import content as C
import content_yontem as Y

SET = C.KOK / "test_seti.json"
SONUC = C.KOK / "test_sonuclari.jsonl"
ATLA = {"yontem", "dogrulama", "kullanici_duzeltmesi", "replik", "web_trend", "ogreticiler", "kaynak_aday", "sarki", "sayfa_kaniti",
        "yorumlar", "dosya_etiketleri", "kutuphane_eslesme", "log", "hata"}


def set_oku():
    try:
        L = json.loads(SET.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    for x in L:                                     # eski biçim: "id" = kullanıcının işi
        if x.get("id") and not x.get("kaynak_id"):
            x["kaynak_id"] = x.pop("id")
    return L


def set_yaz(L):
    SET.write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding="utf-8")


def _sade(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower().replace("ı", "i"))
    return "".join(c for c in s if not unicodedata.combining(c))


def _var(k, metin):
    return any(_sade(x) in metin for x in k.split("|"))


def puanla(d, beklenen):
    y, sonuc = d.get("yontem") or {}, {}
    if beklenen.get("yontem"):
        sonuc["yontem"] = y.get("yontem") in beklenen["yontem"]
    if beklenen.get("kaynak_klip"):
        kk = y.get("kaynak_klip") or {}
        metin = _sade(" ".join(str(kk.get(a) or "") for a in ("ne", "neden", "link")) + " " + (y.get("ozet") or ""))
        sonuc["kaynak_klip"] = all(_var(k, metin) for k in beklenen["kaynak_klip"])
    if beklenen.get("sarki"):
        metin = _sade(json.dumps(d.get("sarki") or {}, ensure_ascii=False))
        sonuc["sarki"] = all(_var(k, metin) for k in beklenen["sarki"])
    if beklenen.get("ozet"):
        metin = _sade((y.get("baslik") or "") + " " + (y.get("ozet") or "") + " " + json.dumps([a.get("ad") for a in y.get("araclar") or []], ensure_ascii=False))
        sonuc["ozet"] = all(_var(k, metin) for k in beklenen["ozet"])
    if beklenen.get("arac"):
        metin = _sade(json.dumps([[a.get("ad"), a.get("ornek")] for a in y.get("araclar") or []], ensure_ascii=False) + json.dumps(y.get("sablon") or {}, ensure_ascii=False))
        sonuc["arac"] = all(_var(k, metin) for k in beklenen["arac"])
    return sonuc


def _deneme_isi(t):
    """Kaydın gizli deneme kopyası: video bir kez iner, sonraki denemeler aynı kopyayı kullanır."""
    tid = t.get("test_id")
    if tid and (C.yol(tid) / "is.json").exists():
        return tid, False
    if t.get("kaynak_id"):
        kay = C.oku(t["kaynak_id"]) or {}
        if not kay:
            raise RuntimeError("Kaynak iş bulunamadı")
        tid = C.yeni(kay.get("link") or "", kay.get("istek") or "", test=True, test_kaynak=t["kaynak_id"])
        hedef = C.yol(tid)
        for f in C.yol(t["kaynak_id"]).iterdir():
            if f.name in ("is.json", "cikti", "yuklemeler", "is_ara"):
                continue
            (shutil.copytree if f.is_dir() else shutil.copy2)(f, hedef / f.name)
        kopya = {k: v for k, v in kay.items() if k not in ATLA and k not in ("id", "ciktilar", "yuklemeler", "silindi", "musteri", "radar")}
        if t.get("sakla"):
            kopya["kaynak"] = dict(kopya.get("kaynak") or {}, baslik="(gizli)", aciklama="", kanal="")
            for f in hedef.glob("kaynak*.info.json"):
                f.unlink()
        C.degistir(tid, lambda d: d.update(kopya, test=True, test_kaynak=t["kaynak_id"], kanit_sakla=bool(t.get("sakla"))))
        return tid, False
    tid = C.yeni(t["link"], t.get("istek") or "", test=True, kanit_sakla=bool(t.get("sakla")))
    return tid, True


def calistir(secim=None, kutuphanesiz=False, yalniz_yeni=False):
    L = set_oku()
    if kutuphanesiz:
        Y.kutuphane_eslesme = lambda cid: []
    denenen = {json.loads(l).get("ad") for l in SONUC.read_text(encoding="utf-8").splitlines() if l.strip()} if SONUC.exists() else set()
    toplam = dogru = 0
    for i, t in enumerate(L):
        if secim and not any(s == str(i) or s.lower() in (t.get("ad") or "").lower() for s in secim):
            continue
        if yalniz_yeni and t.get("ad") in denenen:
            continue
        t0 = time.time()
        try:
            tid, indir = _deneme_isi(t)
            t["test_id"] = tid
            set_yaz(L)
            if indir or not (C.oku(tid) or {}).get("tarif"):
                C.cozumle(tid)                       # indirir, izler ve rehberi yazar
            else:
                Y.coz(tid)
            d = C.oku(tid)
            p = puanla(d, t["beklenen"])
        except Exception as e:  # noqa: BLE001
            d, p = {}, {"hata": str(e)[:200]}
        y = d.get("yontem") or {}
        kayit = {"t": time.time(), "ad": t.get("ad"), "test_id": t.get("test_id"), "sakla": bool(t.get("sakla")), "kutuphanesiz": kutuphanesiz,
                 "sure": round(time.time() - t0), "puan": p, "yontem": y.get("yontem"), "guven": y.get("guven"), "kademe": y.get("kademe"),
                 "baslik": y.get("baslik"), "ozet": (y.get("ozet") or "")[:300], "araclar": [a.get("ad") for a in y.get("araclar") or []],
                 "kaynak_klip": (y.get("kaynak_klip") or {}).get("ne")}
        with SONUC.open("a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        n = sum(1 for v in p.values() if v is True)
        toplam += len([v for v in p.values() if isinstance(v, bool)])
        dogru += n
        print(f"{i:2} {str(t.get('ad'))[:44]:44} {n}/{len(p)} {p} ({kayit['sure']} sn)", flush=True)
    print(f"Toplam: {dogru}/{toplam} doğru")


def ozet(son=True):
    """Her kaydın son denemesi: {ad: puan}."""
    out = {}
    if SONUC.exists():
        for l in SONUC.read_text(encoding="utf-8").splitlines():
            try:
                k = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            out[k.get("ad")] = k
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    calistir([x for x in a if not x.startswith("--")] or None, "--kutuphanesiz" in a, "--yeni" in a)
