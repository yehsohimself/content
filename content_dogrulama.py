"""content_dogrulama.py - "Doğru mu?" geri bildirimi (2026-10-29).

Kullanıcı rehberin altında Doğru · Kısmen · Yanlış der, gerekirse "aslında şöyleydi" yazar. Üç şey olur:
1. Düzeltme o videonun gerçeği sayılır (`is.json kullanici_duzeltmesi`) ve rehber onunla yeniden yazılır.
2. Düzeltmeden genel bir ders çıkar (`content/ogrenme/yontem_dersleri.json`); sonraki bütün incelemelerin istemine girer.
3. Video, cevabı bilinen deneme setine girer (`content/test_seti.json`, content_test): sonraki değişiklikler onunla ölçülür.
"""
import json
import time

import content as C

DERS = C.KOK / "ogrenme" / "yontem_dersleri.json"
KARARLAR = ("dogru", "kismen", "yanlis")

ISTEM = """Bir sistem, bir sosyal medya videosunun nasıl yapıldığını çözdü. Kullanıcı bu çözüme şu kararı verdi: {karar}.
Sistemin söylediği:
- Yöntem kodu: {yontem}
- Başlık: {baslik}
- Özet: {ozet}
- Araçlar: {araclar}
- Orijinal görüntü (kaynak klip): {kaynak}
Kullanıcının notu (videonun gerçeği; kullanıcı biliyor): "{not_}"

Görev 1 - cevap anahtarı: bu videonun DOĞRU cevabını, sonraki çözümlerin otomatik puanlanacağı biçimde yaz. Yalnız kesin bilinenleri koy.
 - yontem: doğru yöntem kodları (capcut_sablon, capcut_elle, yapay_zeka_araci, cekim_kurgu, ekran_kaydi, karisik); makul birden çok kod olabilir.
 - kaynak_klip: orijinal görüntü biliniyorsa, doğru bir çözümün mutlaka anacağı 1-2 sözcük (küçük harf; alternatifler "a|b"); yoksa boş liste.
 - arac: yalnız kesin bilinen araç adları (küçük harf, "a|b"); yoksa boş liste.
 - ozet: doğru çözümün özetinde geçmesi gereken 1-3 kavram sözcüğü (küçük harf, alternatifler "a|b"; ör. "yuz|face" gibi Türkçe ve İngilizce); yoksa boş.
Görev 2 - ders: karar 'dogru' değilse, sistemin bir dahaki BAŞKA videolarda aynı hatayı yapmaması için tek, genel, uygulanabilir ders yaz
(TEK cümle, en çok 35 kelime; bu videoya özgü ad verme; ör. "Konuşan ses görünen karakterlere uymuyorsa, sahnenin sesiyle birlikte başka bir filmden alınıp yüzlerin
değiştirilmiş olabileceğini tart"). 'dogru' ise ders boş.
Yalnız JSON: {{"beklenen": {{"yontem": [], "kaynak_klip": [], "arac": [], "ozet": []}}, "ders": "", "hata": "sistem neyi yanlış saptadı, tek cümle ya da boş"}}"""


def _json(yol, vars_):
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return vars_


def dersler(haric=None, n=12):
    return [x for x in _json(DERS, []) if x.get("ders") and x.get("cid") != haric][-n:]


def dersler_blogu(haric=None):
    """İstemlere giren 'geçmiş hatalardan dersler'. Deneme kopyasında dersin kendi videosu hariç tutulur (ölçüm şişmesin)."""
    L = dersler(haric)
    return "\n".join(f"- {x['ders']}" for x in L) if L else "(henüz yok)"


def kaydet(cid, karar, not_=""):
    import claude_yaz
    if karar not in KARARLAR:
        raise ValueError("Geçersiz karar")
    d = C.oku(cid) or {}
    y = d.get("yontem") or {}
    if not y:
        raise ValueError("Bu videonun rehberi yok.")
    not_ = str(not_ or "").strip()[:1200]
    kayit = {"karar": karar, "not": not_, "t": time.time(),
             "onceki": {"yontem": y.get("yontem"), "baslik": y.get("baslik"), "ozet": y.get("ozet"), "guven": y.get("guven")}}
    C.guncelle(cid, dogrulama=kayit, **({"kullanici_duzeltmesi": not_} if karar != "dogru" and not_ else {}))
    try:
        j = claude_yaz.json_coz(claude_yaz.sor(ISTEM.format(
            karar={"dogru": "DOĞRU", "kismen": "KISMEN DOĞRU", "yanlis": "YANLIŞ"}[karar], yontem=y.get("yontem"), baslik=y.get("baslik") or "-",
            ozet=y.get("ozet") or "-", araclar=", ".join(a.get("ad") or "" for a in y.get("araclar") or []) or "-",
            kaynak=(y.get("kaynak_klip") or {}).get("ne") or "-", not_=not_ or "(not yok)"), model_adi="sonnet")) or {}
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] doğrulama çözümlenemedi: {e}", flush=True)
        j = {}
    b = {k: [str(v).lower() for v in (j.get("beklenen") or {}).get(k) or [] if v] for k in ("yontem", "kaynak_klip", "arac", "ozet")}
    if karar == "dogru" and not b["yontem"]:
        b["yontem"] = [y.get("yontem")]
    b = {k: v for k, v in b.items() if v}
    if b.get("yontem"):
        _teste_ekle(d, b, karar)
    if karar != "dogru" and j.get("ders"):
        L = [x for x in _json(DERS, []) if x.get("cid") != cid]
        L.append({"t": time.time(), "cid": cid, "ders": str(j["ders"])[:400], "hata": str(j.get("hata") or "")[:300], "not": not_[:400]})
        DERS.parent.mkdir(parents=True, exist_ok=True)
        DERS.write_text(json.dumps(L[-60:], ensure_ascii=False, indent=1), encoding="utf-8")
    return {"beklenen": b, "ders": j.get("ders") or ""}


def _teste_ekle(d, beklenen, karar):
    import content_test as T
    L = T.set_oku()
    L = [x for x in L if x.get("kaynak_id") != d["id"] and x.get("id") != d["id"]]
    L.append({"kaynak_id": d["id"], "link": d.get("link"), "ad": ((d.get("kaynak") or {}).get("baslik") or d.get("link") or "")[:80],
              "beklenen": beklenen, "kaynak": f"kullanıcı ({karar})", "t": time.time()})
    T.set_yaz(L)
