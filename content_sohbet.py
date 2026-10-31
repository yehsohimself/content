"""content_sohbet.py - Content'le konuşmak (2026-10-31). Kullanıcı rehberin yanında soru sorar: "Ücretsiz yapabilir miyim?", "Neden CapCut olduğunu
düşünüyorsun?", "3. adımda o düğmeyi bulamadım". Content incelemede ne bulduysa ona dayanarak, bir insan gibi kısa yanıt verir; yanıt sorunun cevabını
bilinmeyen bir şeye bağlıysa (telefon mu bilgisayar mı, kendi fotoğrafı mı) TEK bir karşı soru sorar ve hazır cevaplar önerir. Gerekirse bir eylem önerir:
rehberi yeni bir istekle yeniden yazmak ya da kullanıcının "aslında şöyleydi" bilgisini düzeltme olarak kaydetmek (kullanıcı düğmeye basınca olur).

Yanıt akarak gelir; son satır `@@ {"secenekler": [...], "eylem": {...}}` (sayfa bu satırı göstermez, düğmelere çevirir).
Geçmiş is.json `sohbet` = [{rol: ben|content, metin, secenekler, eylem, t}]. Linksiz genel soru (ana sayfa) da aynı yolla, kayıtsız.
"""
import json
import re
import time

import content as C

GECMIS = 14
AYRAC = "@@"

SISTEM = """Sen Content'sin: sosyal medya videolarının nasıl yapıldığını çözen, işini bilen ama samimi bir video yapımcısı. Kullanıcıyla sohbet ediyorsun.
Nasıl konuşursun:
- İnsan gibi, kısa ve sıcak; "siz" diye hitap et. Önce doğrudan cevap, gerekiyorsa en çok 4 kısa madde. Başlık, "İşte", "Harika soru" gibi dolgu yok.
- Teknik terim yerine gündelik dil (ör. "model" yerine "yapay zekâ aracı", gerekirse aracın adını yaz).
- Yalnız aşağıdaki inceleme bulgularına ve genel bilgine dayan. Bulgularda olmayan bir şeyi kesinmiş gibi söyleme; emin değilsen "emin değilim, şunu
  gösteriyor" de. Uygulama menüleri değişebilir; düğme adından emin değilsen benzerini aramasını söyle.
- Cevap kullanıcının bilmediğin bir durumuna bağlıysa (telefon mu bilgisayar mı, ücretsiz mi, kendi fotoğrafı mı, hangi uygulama sürümü) uzun uzun
  her ihtimali anlatma: kısa bir ön bilgi ver ve TEK bir karşı soru sor; hazır cevapları seçenek olarak ekle. Her mesajda soru sorma; gerekmiyorsa sorma.
- Kullanıcı videonun aslında nasıl yapıldığını söylüyorsa (ör. "bu aslında Kling'le yapıldı") teşekkür et, bunun neyi değiştirdiğini söyle ve
  "duzeltme" eylemi öner. Kullanıcı rehberin farklı bir yolla (telefonda, ücretsiz, kendi kedisiyle) yazılmasını istiyorsa kısaca nasıl değişeceğini
  söyle ve "yeniden" eylemi öner. Eylemi kendin yapmış gibi konuşma; kullanıcı düğmeye basınca olur.
Yanıtının EN SON satırı tam olarak şu biçimde olsun (başka bir şey ekleme, kod bloğu kullanma):
@@ {"secenekler": ["kullanıcının tek dokunuşla verebileceği 0-4 kısa cevap ya da sonraki soru"], "eylem": null}
eylem yalnız gerekiyorsa: {"tur": "yeniden", "istek": "rehberin yeniden yazılacağı istek, kullanıcının ağzından tek cümle", "etiket": "düğme yazısı (2-4 kelime)"}
ya da {"tur": "duzeltme", "not": "videonun gerçeği, kullanıcının söylediği", "etiket": "düğme yazısı"}.
Karşı soru sorduysan seçenekler o sorunun cevapları olsun; sormadıysan kullanıcının sorabileceği 2-3 doğal sonraki soru."""

GENEL_EK = """Şu an elinde incelenmiş bir video yok; kullanıcı ana sayfada genel bir soru soruyor. Bildiğin kadarıyla cevap ver; belirli bir video söz
konusuysa linkini yapıştırmasını iste (Content videoyu izleyip kanıtlarla çözer). Bu sohbette eylem önerme (eylem: null)."""


def _kisa(v, n):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n] + "…"


def baglam(d):
    """İncelemenin konuşmaya giren özeti: video bilgisi, izlenenler, kanıtlar ve rehberin kendisi."""
    k = d.get("kaynak") or {}
    t = d.get("tarif") or {}
    y = d.get("yontem") or {}
    p = []
    p.append(f"VİDEO: {d.get('link', '')}\nBaşlık: {k.get('baslik', '')} · Kanal: {k.get('kanal', '')} · Süre: {round(k.get('sure') or 0, 1)} sn"
             f" · {'dikey' if (k.get('h') or 0) > (k.get('w') or 0) else 'yatay'} · İzlenme: {k.get('izlenme', '')}")
    if d.get("istek"):
        p.append(f"KULLANICININ İSTEĞİ: {d['istek']}")
    if d.get("kullanici_duzeltmesi"):
        p.append(f"KULLANICININ DÜZELTMESİ (videonun gerçeği): {d['kullanici_duzeltmesi']}")
    if t:
        p.append("VİDEODA NE VAR (izleyerek): " + _kisa({x: t.get(x) for x in ("ozet", "tur", "kisiler", "ses", "kamera", "yapay_zeka", "sahneler", "yazilar")
                                                     if t.get(x)}, 9000))
    if d.get("sayfa_kaniti"):
        p.append("PLATFORM SAYFASI: " + _kisa(d["sayfa_kaniti"], 3000))
    if d.get("sarki"):
        p.append("ŞARKI: " + _kisa(d["sarki"], 600))
    if d.get("web_trend"):
        p.append("WEB'DE AKIM: " + _kisa(d["web_trend"], 2000))
    if d.get("benzerler"):
        p.append("BENZER VİDEOLAR (ses/görüntü benzerliği): " + _kisa([{x: b.get(x) for x in ("baslik", "ses", "gorsel", "link")} for b in d["benzerler"][:6]], 1500))
    if d.get("ogreticiler"):
        p.append("ÖĞRETİCİ VİDEOLAR: " + _kisa([{x: o.get(x) for x in ("baslik", "link")} for o in d["ogreticiler"][:4] if isinstance(o, dict)], 1200))
    if y:
        p.append("SENİN YAZDIĞIN REHBER: " + _kisa({x: y.get(x) for x in ("baslik", "ozet", "yontem", "guven", "kademe", "kanit", "araclar", "sablon", "kaynak_klip",
                                                                       "degisen_katmanlar", "gerekenler", "adimlar", "sik_hatalar", "emin_olmadiklarim",
                                                                       "bulunamayanlar", "claude_yolu") if y.get(x)}, 16000))
    elif d.get("durum") in ("cozuluyor", "planlaniyor"):
        son = [m for _, m in (d.get("log") or [])[-8:]]
        p.append("DURUM: inceleme sürüyor; rehber henüz yazılmadı. Şu ana kadar: " + " / ".join(son))
    return "\n\n".join(p)


def ayir(metin):
    """Yanıt metni ile son satırdaki @@ JSON'unu ayırır."""
    i = metin.rfind(AYRAC)
    ek = {}
    if i >= 0:
        try:
            ek = json.loads(metin[i + len(AYRAC):].strip().strip("`"))
        except Exception:  # noqa: BLE001
            m = re.search(r"\{.*\}", metin[i:], re.S)
            try:
                ek = json.loads(m.group(0)) if m else {}
            except Exception:  # noqa: BLE001
                ek = {}
        metin = metin[:i]
    sec = [str(s)[:80] for s in (ek.get("secenekler") or []) if str(s).strip()][:4]
    ey = ek.get("eylem") if isinstance(ek.get("eylem"), dict) else None
    if ey and ey.get("tur") not in ("yeniden", "duzeltme"):
        ey = None
    if ey:
        ey = {"tur": ey["tur"], "etiket": str(ey.get("etiket") or ("Rehberi böyle yaz" if ey["tur"] == "yeniden" else "Düzeltmeyi kaydet"))[:40],
              **({"istek": str(ey.get("istek") or "")[:600]} if ey["tur"] == "yeniden" else {"not": str(ey.get("not") or "")[:1000]})}
        if not (ey.get("istek") or ey.get("not")):
            ey = None
    return metin.strip(), sec, ey


def akis(d, soru, gecmis=None, dil="tr"):
    """Yanıtı parça parça verir (üreteç). d None ise genel (linksiz) sohbet."""
    import claude_yaz
    if not claude_yaz.hazir():
        raise RuntimeError("Claude şu an kullanılamıyor; biraz sonra yeniden deneyin.")
    konusma = "\n".join(f"{'KULLANICI' if m.get('rol') == 'ben' else 'SEN'}: {m.get('metin', '')}" for m in (gecmis or [])[-GECMIS:])
    sistem = SISTEM + ("\n" + GENEL_EK if d is None else "") + ("\nKullanıcıya İngilizce yanıt ver; @@ satırındaki metinler de İngilizce olsun." if dil == "en" else "")
    istem = ((("İNCELEME BULGULARI:\n" + baglam(d)) if d else "(incelenmiş video yok)")
             + ("\n\nŞİMDİYE KADARKİ SOHBET:\n" + konusma if konusma else "") + f"\n\nKULLANICININ YENİ MESAJI: {soru}")
    try:
        yield from claude_yaz.sor_akis(istem, sistem, zaman_asimi=240)
    except claude_yaz.ClaudeHata as e:
        raise RuntimeError(f"Claude yanıt veremedi: {e}") from e


def kaydet(cid, ben, yanit, secenekler, eylem):
    now = time.time()

    def f(d):
        L = d.setdefault("sohbet", [])
        L.append({"rol": "ben", "metin": ben, "t": now})
        L.append({"rol": "content", "metin": yanit, "secenekler": secenekler, "eylem": eylem, "t": time.time()})
        del L[:-60]
    C.degistir(cid, f)
