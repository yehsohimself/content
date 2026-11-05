"""content_akim.py - bir akımı beş ayrı kanaldan tanımak (2026-11-05).

Kullanıcı: "Bir akım görselden de anlaşılabilir, sesten de, konuşmalardan da; bazen bir hareketten ya da geçişten, ya da video üstü süperden." Eskiden akım yalnız şarkı adı
ve TikTok'un önerdiği sözcükle aranıyordu; şarkısız konuşan hamamböceği videosunda öneri "hamam" olduğu için sabun ve sauna videolarıyla karşılaştırılmıştı.

kalip(cid, ...): akımlar çeşitlenir (kullanıcı: hamamböceği akımında herkes başka şey söylüyor, akım görselden geliyor; bazılarına sonradan müzik ekleniyor). Bu yüzden tek videonun izi yetmez: bulunan
örnekler yan yana konur, ne sabit, ne bazen, ne her videoda farklı, hangi kollar var, çıkarılır. Rehberde sabit olan korunur, değişen kişinin kendi malzemesi olur.

imza(cid): Claude videonun ızgaralarına, konuşmasına ve yazılarına bakıp her kanal için AYIRT EDİCİ olanı ve onu bulacak aramaları yazar (hiçbir kanal zorunlu değil).
Bu aramalar web taramasına, öğretici ve benzer video aramasına gider; `suz` adayları indirmeden önce başlıklarından eler. Sonuç is.json `akim_imza`; hangi kanalın ne bulduğu web taramasından gelir.
"""
import json
import re

KANAL_AD = {"goruntu": "Görüntü", "ses": "Ses", "konusma": "Konuşma", "hareket": "Hareket ve geçiş", "super": "Üstteki yazı"}

IMZA = """Bir kısa videonun hangi AKIMA ya da kalıba ait olduğunu bulacağız. Akım her zaman şarkıdan anlaşılmaz: bazen görüntü fikrinden (konuşan hamamböcekleri), bazen konuşmadan (herkesin
aynı sözü tekrar etmesi), bazen sesten, bazen bir hareket ya da geçişten (giysi değiştirme geçişi, yüze doğru kamera çarpması, dans figürü, nesnenin başka şeye dönüşmesi), bazen üstteki yazının kalıbından ("POV:", "X vs Y", sayaç) anlaşılır.

Video: {sure:.1f} sn. Ekte sırayla kare ızgaraları var (köşede "S<sahne> · <saniye>s").
Konuşma: {ses}
Üstteki yazılar: {yazilar}
Şarkı bilgisi: {sarki}
{etiket}

Her kanal için kendin bak ve yalnız AYIRT EDİCİ olanı yaz. O kanalda akımı ele verecek bir şey yoksa "ne" boş ve "aramalar" boş olsun; zorlama. Sıradan bir kesme, düz konuşma, hareketsiz kamera ayırt edici değildir.
Aramalar, BAŞKA İNSANLARIN aynı kalıpta yaptığı videoları ve bu akımı anlatan sayfaları bulmalı: bu videonun kendisine özgü ad ve ayrıntı değil, kalıbın genel adı. Görüntü ve hareket aramalarını Türkçe ve İngilizce; konuşma aramalarını konuşmanın dilinde ve akılda kalan cümleyi tırnak içinde yaz.
Kişi/karakter tanıdıksa adını yazabilirsin; emin değilsen betimle. Tek başına anlamsız kısa sözcük ("hamam" gibi) arama olamaz.

Yalnız JSON:
{{"goruntu": {{"ne": "en ayırt edici görsel fikir, tek cümle", "aramalar": ["talking cockroach AI video", "konuşan hamamböceği videosu"]}},
 "ses": {{"ne": "şarkı dışında ayırt edici ses varsa (ünlü bir ses kaydı, efekt, belli bir ses tonu)", "aramalar": []}},
 "konusma": {{"ne": "akılda kalan söz, harfi harfine", "aramalar": ["\\"...\\" tiktok"]}},
 "hareket": {{"ne": "ayırt edici hareket ya da geçiş, kaçıncı saniyede", "aramalar": []}},
 "super": {{"ne": "üstteki yazının kalıbı", "aramalar": []}},
 "en_guclu": "goruntu|ses|konusma|hareket|super"}}"""

SUZ = """Bir videonun ait olabileceği akımı bulmak için YouTube'da arama yaptık. Video şöyle: {imza}
Aşağıdaki sonuçlardan yalnız AYNI KALIBI ya da aynı akımı taşıması MÜMKÜN olanları seç (başlık ve kanala bakarak). Sözcük tesadüfen tutmuşsa (hamam böceği videosu ararken hamam sabunu, sauna) alma. Emin değilsen al; açıkça ilgisizleri ele.
{liste}
Yalnız JSON: {{"sec": [numaralar]}}"""


def _temiz(y):
    out = {}
    for k in KANAL_AD:
        v = y.get(k) if isinstance(y.get(k), dict) else {}
        ne = str(v.get("ne") or "").strip()[:240]
        ara = [str(a).strip()[:90] for a in (v.get("aramalar") or []) if len(str(a).strip()) >= 8][:3]
        if ne or ara:
            out[k] = {"ne": ne, "aramalar": ara}
    if out:
        out["en_guclu"] = y.get("en_guclu") if y.get("en_guclu") in out else next(iter(out))
    return out


def imza(cid, izgara, sarki=None, etiketler=""):
    """Kanal kanal ayırt edici izler ve aramalar. Claude yoksa {}: arama eski yolla sürer."""
    import claude_yaz
    import content as C
    d = C.oku(cid)
    t, k = d.get("tarif") or {}, d.get("kaynak") or {}
    yaz = "; ".join(f"{y['sn']:.1f} sn: {y['metin']}" for y in C.gercek_yazilar(t)) or "(yok)"
    istem = IMZA.format(sure=float(k.get("sure") or 0), ses=(t.get("ses_yazisi") or "(konuşma yok)")[:900], yazilar=yaz[:700],
                        sarki=json.dumps(sarki, ensure_ascii=False) if sarki else "(bulunamadı)", etiket=f"Etiketler: {etiketler[:300]}" if etiketler else "")
    try:
        y = claude_yaz.json_coz(claude_yaz.sor_gorsel(istem, [str(x) for x in izgara[:8]], model_adi="sonnet")) or {}
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] akım imzası çıkarılamadı: {e}", flush=True)
        return {}
    o = _temiz(y)
    C.guncelle(cid, akim_imza=o)
    return o


def aramalar(imza_, en_cok=8):
    """En güçlü kanal önce, kanal başına sırayla."""
    if not imza_:
        return []
    sira = [imza_.get("en_guclu")] + [k for k in KANAL_AD if k != imza_.get("en_guclu")]
    out = []
    for i in range(3):
        for k in sira:
            a = (imza_.get(k) or {}).get("aramalar") or []
            if i < len(a) and a[i] not in out:
                out.append(a[i])
    return out[:en_cok]


def metin(imza_):
    if not imza_:
        return "(çıkarılamadı)"
    return "\n".join(f"- {KANAL_AD[k]}: {imza_[k]['ne']}" for k in KANAL_AD if (imza_.get(k) or {}).get("ne")) or "(ayırt edici iz yok)"


def suz(adaylar, imza_):
    """İndirmeden önce başlıktan eleme; yalnız imza varken. Hata olursa adaylar aynen döner."""
    import claude_yaz
    if not imza_ or len(adaylar) < 2:
        return adaylar
    try:
        liste = "\n".join(f"{i + 1}. {a['baslik']} · {a['kanal']} · {a['sure']} sn" for i, a in enumerate(adaylar))
        y = claude_yaz.json_coz(claude_yaz.sor(SUZ.format(imza=metin(imza_), liste=liste), model_adi="sonnet", zaman_asimi=120)) or {}
        sec = [adaylar[n - 1] for n in y.get("sec") or [] if isinstance(n, int) and 0 < n <= len(adaylar)]
        return sec if "sec" in y else adaylar
    except Exception:  # noqa: BLE001
        return adaylar


KALIP = """Bir kısa videonun ait olduğu akımı anlamaya çalışıyoruz. Akımlar çeşitlenir: bir akımda her videoda bambaşka şeyler söylenir ama görüntü fikri aynıdır; başka akımda görüntü herkeste farklıdır ama ses aynıdır;
bazılarına sonradan belli bir müzik eklenir, hepsine değil. Bir tek videodan bunu anlayamazsın; aşağıdaki örnekleri yan yana koyarak ne SABİT, ne BAZEN, ne HER VİDEODA FARKLI, onu bul.

BU VİDEO
Akımı ele verebilecek izler: {imza}
Konuşma: {ses}
Şarkı: {sarki}

BAŞKA VİDEOLAR (arama sonuçları; hepsi aynı akımdan olmayabilir)
{liste}

Ekte her örnek için yan yana kare şeritleri var (üst sıra bu video, alt sıra örnek; sıra: {sira}).

Kurallar: Önce hangi örneklerin gerçekten aynı akımdan olduğuna karar ver; sözcük benzerliği yetmez. Öğretici videolar akımın örneği değildir ama akımın adını ve kurallarını söyleyebilir. "Sabit" demek için bu videoyla birlikte en az iki aynı akım örneğinde görmüş olmalısın; görmediğini yazma.
Konuşma metinleri örneklerde farklıysa konuşma akımın parçası değildir; aynı söz tekrar ediyorsa parçasıdır. Müzik/ses için ses benzerliği sayısına ve konuşma metnine bak. Aynı akımdan yeterli örnek yoksa "emin": "dusuk" yaz, sabit boş kalsın.

Yalnız JSON, metinler Türkçe ve sade. Okur numaraları görmüyor: metinlerde örnek numarası ("1'de", "(2)", "bu videoyla birlikte 1 ve 3'te") YAZMA; numara yalnız "ayni" ve "ornekler" listelerinde.
{{"akim_adi": "akımın en çok kullanılan adı (örneklerden; yoksa boş)", "ayni": [aynı akımdan örneklerin numaraları], "emin": "yuksek|orta|dusuk",
 "kanallar": {{"goruntu": "sabit|bazen|degisen|yok", "ses": "...", "konusma": "...", "hareket": "...", "super": "..."}},
 "sabit": ["herkesin aynen yaptığı, tek cümle"], "bazen": ["bazılarında olan"], "degisen": ["her videoda farklı olan, herkesin kendisinin koyduğu"],
 "kollar": [{{"ad": "akımın bir kolu (kısa)", "ne": "tek cümle", "ornekler": [numaralar]}}], "bu_video": "bu video akımın hangi kolunda, kendine özgü ne katmış, tek cümle"}}"""


def _yazi_dok(video):
    """Örnek videonun konuşması; ayrı süreçte. Olmazsa boş."""
    import subprocess
    import sys as _s
    from pathlib import Path
    try:
        r = subprocess.run([_s.executable, str(Path(__file__).resolve().parent / "sesnot.py"), str(video), ""], capture_output=True, text=True, timeout=180)
        return (json.loads(r.stdout).get("metin") or "")[:400]
    except Exception:  # noqa: BLE001
        return ""


def _numarasiz(m):
    """Modelin metne sızdırdığı örnek numaraları: "(1)", "(bu videoyla birlikte 1, 2 ve 3'te görüldü)", "1'e yakın"."""
    m = re.sub(r"\s*\((?:[^()]*\b\d[^()]*(?:görüldü|görülüyor|var)|bu video(?:yla|, )?[^()]*\d[^()]*|\d+(?:\s*(?:,|ve)\s*\d+)*)\)", "", str(m))
    return re.sub(r"\s+", " ", re.sub(r"\s*\((?:en çok )?\d+'?[a-zçğıöşü]*\s*yakın\)", "", m)).strip()


def kalip(cid, benzerler, imza_, sarki=None, en_cok=4):
    """Akımın örneklerini karşılaştırır: ne sabit, ne bazen, ne değişiyor, hangi kollar var. is.json `akim_kalip`. Örnek yoksa {}."""
    import claude_yaz
    import content as C
    from pathlib import Path
    ornek = [b for b in benzerler if b.get("serit") and Path(b["serit"]).exists()][:en_cok]
    if not ornek:
        return {}
    klasor = C.yol(cid) / "is_ara" / "benzer"
    for b in ornek:
        v = klasor / f"{b.get('id')}.mp4"
        b["konusma"] = _yazi_dok(v) if v.exists() else ""
    d = C.oku(cid)
    liste = "\n".join(f"{i + 1}. [{b.get('baslik')}] kanal {b.get('kanal')}, {b.get('sure')} sn; sese benzerlik {b.get('ses')}, görüntüye benzerlik {b.get('gorsel')}; konuşması: {b['konusma'] or '(konuşma yok ya da yazılamadı)'}"
                      for i, b in enumerate(ornek))
    try:
        y = claude_yaz.json_coz(claude_yaz.sor_gorsel(KALIP.format(imza=metin(imza_), ses=((d.get("tarif") or {}).get("ses_yazisi") or "(konuşma yok)")[:500], sarki=json.dumps(sarki, ensure_ascii=False) if sarki else "(yok)",
                                                                   liste=liste, sira=", ".join(str(i + 1) for i in range(len(ornek)))), [b["serit"] for b in ornek], model_adi="sonnet")) or {}
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] akım karşılaştırılamadı: {e}", flush=True)
        return {}

    def L(a, n=5):
        return [_numarasiz(x)[:200] for x in (y.get(a) or []) if str(x).strip()][:n]
    def bag(n):
        return ornek[n - 1].get("link") if isinstance(n, int) and 0 < n <= len(ornek) else None
    o = {"akim_adi": str(y.get("akim_adi") or "")[:80], "emin": y.get("emin") if y.get("emin") in ("yuksek", "orta", "dusuk") else "dusuk", "sabit": L("sabit"), "bazen": L("bazen"), "degisen": L("degisen"), "bu_video": _numarasiz(y.get("bu_video") or "")[:240],
         "kanallar": {k: v for k, v in (y.get("kanallar") or {}).items() if k in KANAL_AD and v in ("sabit", "bazen", "degisen")},
         "ornekler": [{"link": bag(n), "baslik": ornek[n - 1].get("baslik"), "konusma": ornek[n - 1].get("konusma", "")[:160]} for n in y.get("ayni") or [] if bag(n)],
         "kollar": [{"ad": str(x.get("ad") or "")[:60], "ne": str(x.get("ne") or "")[:200], "linkler": [bag(n) for n in x.get("ornekler") or [] if bag(n)]} for x in (y.get("kollar") or []) if isinstance(x, dict) and x.get("ad")][:4], "bakilan": len(ornek)}
    if not o["ornekler"]:                       # aynı akımdan örnek yoksa "sabit" iddia edilemez
        o.update(sabit=[], bazen=[], degisen=[], kollar=[], kanallar={}, emin="dusuk")
    C.guncelle(cid, akim_kalip=o)
    return o


def kalip_metni(o):
    if not o or not o.get("ornekler"):
        return "(aynı akımdan başka örnek bulunamadı; neyin sabit olduğu bilinmiyor, rehberde 'akımın kuralı' diye kesin konuşma)"
    return (f"Akım: {o.get('akim_adi') or 'adı bulunamadı'} ({len(o['ornekler'])} örnek karşılaştırıldı, güven {o['emin']}). SABİT: {'; '.join(o['sabit']) or '-'}. BAZEN: {'; '.join(o['bazen']) or '-'}. "
            f"HER VİDEODA FARKLI: {'; '.join(o['degisen']) or '-'}. Kollar: {'; '.join(k['ad'] + ': ' + k['ne'] for k in o['kollar']) or '-'}. Bu video: {o.get('bu_video') or '-'}")


def kanal_temizle(j):
    """Web taramasının kanal kanal bulguları; bağlantısı ya da bulgusu olmayan satır atılır."""
    out = []
    for x in (j or {}).get("kanallar") or []:
        if isinstance(x, dict) and x.get("kanal") in KANAL_AD and x.get("bulgu"):
            lk = str(x.get("link") or "")
            out.append({"kanal": x["kanal"], "ad": KANAL_AD[x["kanal"]], "bulgu": str(x["bulgu"])[:220], "link": lk if re.match(r"https?://", lk) else ""})
    return out
