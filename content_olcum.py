"""content_olcum.py - videoyu sahne sahne ölçmek: hangi sahne gerçek çekim, hangisi yapay zekâ, hangisi şablon; ses ve yazı katmanı (2026-11-05).

Ölçümü açık kaynak rea-video (JuneYaooo/rea-video, Apache-2.0) yapar: kare hızı izi, sensör gürültüsü, tek düzlem kayma, dosya etiketleri, tempo, anahtar,
ses ayrımı. Ayrı ortamda (.venv-rea) ve ayrı süreçte çalışır; yoksa ya da hata verirse Content eskisi gibi sürer. Aracın kendi "görsel gözden geçirme"
adımını Claude yapar (`gozden_gecir`): araç ölçer, Claude bakar, araç ikisini birleştirir. Sonuç is.json `olcum`; ham çıktı is_ara/rea/ (yeniden çözümde kullanılır).

Dürüstlük sınırları (kendi test setimizde görüldü, kod bunları eler):
- Çince yazı tanıma Latin yazıda çöp üretiyor ("三", "二"); Çince harfli ya da tek harfli yazı, videoda Vision okumadıysa alınmaz.
- Dosyanın içinde rastgele geçen "veo" gibi zayıf izler ("Google Veo?") kanıt sayılmaz; yalnız gerçek etiketler.
- "Yeniden yazılan istem" videonun GERÇEK istemi değildir: aynısını üretecek bir istemdir, ekranda da böyle yazar.
Elle: python content_olcum.py <cid>   (ölçer, gözden geçirir, is.json'a yazar)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import claude_yaz
import content as C

KLASOR = Path(__file__).resolve().parent
REA_PY = KLASOR / ".venv-rea" / "bin" / "python"
EN_UZUN = 300          # sn; daha uzun videoda sahne ölçümü yapılmaz (ölçüm videonun 3-5 katı sürüyor)
GRUP = 8               # bir Claude çağrısına giren sahne sayısı
EN_COK_BAKIS = 40      # gözle bakılacak en çok sahne (fazlası yalnız ölçümle kalır)

TUR_AD = {"live_action": "Gerçek çekim", "ai_video": "Yapay zekâ videosu", "avatar": "Konuşan avatar", "cg_3d": "3D animasyon", "anim_2d": "2D animasyon",
          "stop_motion": "Stop motion", "code_render": "Hareketli grafik", "screen_capture": "Ekran kaydı", "still_motion": "Kayan fotoğraf", "static_hold": "Durağan görsel"}
ISLEM_AD = {"face_swap": "yüz değiştirilmiş", "lip_sync": "dudak uyumu yapılmış", "restyle": "görünümü yapay zekâyla değiştirilmiş", "outfit_swap": "kıyafet değiştirilmiş",
            "bg_replace": "arka plan değiştirilmiş", "object_edit": "nesne eklenmiş ya da silinmiş", "beautify": "yüz güzelleştirilmiş"}
MUZIK_AD = {"ai_generated": "yapay zekâyla üretilmiş olabilir", "existing_library": "hazır müzik kütüphanesinden olabilir", "popular_song": "bilinen bir şarkı olabilir"}
SES_AD = {"tts": "yapay ses olabilir", "ai_video_native": "videoyla birlikte üretilmiş olabilir", "human_recording": "gerçek insan sesi olabilir"}
EFEKT_AD = {"library_editor": "kurguda eklenmiş olabilir", "ai_native": "videoyla birlikte üretilmiş olabilir", "live_sync": "çekim anının sesi olabilir"}
CJK = re.compile(r"[㐀-鿿぀-ヿ가-힯]")


def hazir():
    return REA_PY.exists() and bool(C.ayar().get("olcum", True))


def _klasor(cid):
    return C.yol(cid) / "is_ara" / "rea"


def _rea(*arg, zaman=600):
    env = dict(os.environ, REA_VIDEO_HOME=str(C.KOK / ".rea"), PYTHONUNBUFFERED="1")
    return subprocess.run(["nice", "-n", "10", str(REA_PY), "-m", "rea_video", *arg], capture_output=True, text=True, timeout=zaman, env=env, stdin=subprocess.DEVNULL)


def olc(cid):
    """rea-video'yu çalıştırır; breakdown'u döndürür. Aynı kaynak için bir kez ölçer."""
    d = C.oku(cid)
    k = d.get("kaynak") or {}
    if k.get("statik") or float(k.get("sure") or 0) > EN_UZUN:
        return None
    video = C.yol(cid) / "kaynak.mp4"
    if not video.exists():
        return None
    cikti = _klasor(cid)
    br = cikti / "breakdown.json"
    if br.exists() and br.stat().st_mtime >= video.stat().st_mtime:
        return json.loads(br.read_text(encoding="utf-8"))
    cikti.parent.mkdir(parents=True, exist_ok=True)
    r = _rea("decompose", str(video), "-o", str(cikti), zaman=max(600, int(float(k.get("sure") or 60) * 12)))
    if r.returncode != 0 or not br.exists():
        raise RuntimeError((r.stderr or r.stdout or "ölçüm başarısız")[-400:])
    return json.loads(br.read_text(encoding="utf-8"))


GOZDEN = """Bir videonun çekimlerini tek tek inceleyen deneyimli bir video yapım uzmanısın. Bir ölçüm aracı bu videoyu çekimlere ayırdı ve her çekimi piksellerinden ölçtü. Ekte
her çekim için aralıklı 9 kareyi zaman sırasıyla gösteren bir ızgara var (köşede saniye; sırası sonda yazılı). Bağımsız karar ver: her çekimin görüntüsü NASIL üretilmiş?
{kunye}
İki yönde de hata yapılıyor ve ikisi de kötü: gerçek bir videoya "yapay zekâ" demek, yapay zekâya "gerçek" demek kadar yanlıştır. Önce videonun GENELİNE bak, sonra çekimlere.

GERÇEK ÇEKİMİN İZLERİ: tanınan gerçek bir içerik üreticisi; aynı kişinin çekimden çekime tutarlı yüzü ve aksesuarı; beş parmaklı doğru eller, cihaz ve ambalajlarda okunur yazı; ışık ve mekânın çekimler boyunca tutarlılığı.
BUNLAR YAPAY ZEKÂ KANITI DEĞİLDİR: hareket bulanıklığı (hızlı el, sıçrayan nesne, konuşan ağızda dişlerin bulanıklaşması); sıkıştırma kaybı; kareler ayrı anlardan olduğu için bir nesnenin iki kare arasında yer değiştirmesi, düşmesi, görünüp kaybolması (lastik kesilip düşer, el çerçeveden çıkar); buhar ve yansıma; hızlandırılmış kurgu; güzellik filtresi.
YAPAY ZEKÂ KANITI: aynı nesnenin birbirine çok yakın karelerde başka bir şeye DÖNÜŞMESİ; sahnede sebepsiz değişen kişi/kıyafet/nesne; bozuk harfler, tuhaf parmaklar; fiziğe aykırı davranış; sahneye ait olmayan eylem. Tek bir küçük şüphe yetmez; emin değilsen gerçek çekim tarafında kal ve olasılığı paylaştır.

TÜRLER (label_probs anahtarları, toplamı 1):
live_action = gerçek kamerayla çekim; ai_video = yapay zekâ video modeli (metinden ya da görselden üretim, başka videodan hareket aktarma dahil);
avatar = tek portre fotoğrafın sesle konuşturulması; cg_3d = Blender/C4D gibi 3D; anim_2d = çizim, Live2D, After Effects karakter animasyonu; stop_motion = kil, keçe, kâğıt kare kare;
code_render = hazır şablon/hareketli grafik/metin kartı (Canva, CapCut metin, After Effects, Remotion); screen_capture = ekran kaydı ya da ekran görüntüsü;
still_motion = tek bir fotoğrafın yakınlaştırılıp kaydırılması; static_hold = hareketsiz görsel.

KARIŞANLAR:
- Gerçek çekim mi yapay zekâ mı: gerçekte gürültü kareler arasında değişir; el, yazı, uzaktaki insanlar düzgün; kumaş, sıvı, çarpma fiziğe uyar. Yapay zekâda cilt ve ışık fazla kusursuz, arkadaki
  yazılar bozuk, nesne kenarları kaynar, hareket yavaş ve süzülür, çekim sonunda donma olabilir. Yalnız "güzel görünüyor" diye karar verme.
- Platformdan indirilmiş videoda sıkıştırma gürültüyü sildiği için "gürültü yok" tek başına yapay zekâ demek DEĞİLDİR; ölçüm bunu not ettiyse görüntüye daha çok güven.
- 24 kare izi hem yapay zekâda hem sinema kamerasında olur. Yapay zekâ gibi görünen dizi/film görüntüsü sinema çekimi olabilir.
- Gerçek çekim üstüne yapay zekâ işlemi varsa tür live_action kalır ve ai_edits doldurulur; hareket gerçek ama kişi ve dünya tamamen değişmişse (hareket aktarma, tam görünüm değişimi) tür ai_video olur.
- Bilinen bir filmin ya da ünlünün görünümü "gerçek" demek değildir: yapay zekâ bilinen sahneleri, kostümleri, sinematik ışığı çok iyi taklit eder. "Sinema gibi görünüyor" gerçek çekim kanıtı DEĞİLDİR. Sahneye
  ait olmayan eylem (takım elbiseli ajanların futbol oynaması, karakterin kendi dünyasında yapmayacağı şey), nesnelerin birbirine dönüşmesi, kareden kareye değişen kıyafet ve yüz ayrıntısı, bir karede var ötekinde yok olan parçalar yapay zekâ işaretidir.
- Kartta oynayan metin hareketli grafiktir; üstteki altyazı çekimin türünü değiştirmez.
Görmediğin şeyi yazma. Emin değilsen olasılığı paylaştır (ör. ai_video .55, live_action .45) ve kanıtta neyi göremediğini söyle.

ÇEKİMLER:
{liste}

Yalnız JSON ver:
{{"shots": [{{"id": "shot_001",
  "label_probs": {{"ai_video": .8, "live_action": .2}},
  "image_source": "ai_image|photo|graphic|screenshot|unknown",
  "evidence": ["bu karede gördüğün somut kanıt, Türkçe, en çok 3 kısa madde"],
  "description": "çekimde ne oluyor, kişisiz ve sade, Türkçe tek cümle",
  "ai_edits": [{{"kind": "face_swap|lip_sync|restyle|outfit_swap|bg_replace|object_edit|beautify", "evidence": "kısa"}}],
  "replication": {{"image_prompt": "yalnız yapay zekâ/3D çekimlerde: ilk kareyi üretecek İngilizce görsel istemi (özne, kompozisyon, ışık, stil)",
                   "video_prompt_en": "yalnız yapay zekâ/3D çekimlerde: bu çekimi üretecek İngilizce video istemi (hareket, kamera, bitiş durumu; 'no ...' yazma)"}},
  "cekim": "yalnız gerçek çekimlerde, Türkçe tek cümle: kamera (telefon/kamera, elde/sabit), kadraj, ışık, ölçümlere ve karelere dayanarak; uydurma"}}]}}
Her çekim için bir kayıt; istemleri yapay zekâ ya da 3D olmayan çekimlerde boş bırak."""


def _kunye(d):
    k = d.get("kaynak") or {}
    if d.get("kanit_sakla") or k.get("baslik") in (None, "", "(gizli)"):
        return ""
    return f"Video: {k.get('baslik') or ''} · hesap: {k.get('kanal') or ''} (bilinen bir üreticiyse bunu hesaba kat; yalnız başına kanıt değildir)."


def _liste(sira):
    L = []
    for s in sira:
        det = (s.get("deterministic") or {})
        en = sorted((det.get("probs") or {}).items(), key=lambda kv: -kv[1])[:2]
        L.append(f"{s['id']} ({s['start']:.1f}-{s['end']:.1f} sn): ölçüm tahmini {', '.join(f'{a} %{round(b * 100)}' for a, b in en)}; ölçüm notları (Çince olabilir): "
                 + " / ".join(x for x in (det.get("evidence") or [])[:6] if "?" not in x and "元数据" not in x)
                 + ("; ölçülen çekim özellikleri: " + "; ".join(f"{a}: {v.get('result')}" for a, v in (s.get("aspects") or {}).items() if isinstance(v, dict) and v.get("result"))[:400] if s.get("aspects") else ""))
    return "\n".join(L)


def _sec(shots):
    """Gözle bakılacak çekimler: uzun süreli olanlar önce; art arda aynı türden kısa çekimler seyreltilir."""
    if len(shots) <= EN_COK_BAKIS:
        return list(shots)
    return sorted(sorted(shots, key=lambda s: -s["duration"])[:EN_COK_BAKIS], key=lambda s: s["index"])


def _izgara(cid, s):
    """Çekimin 3x3 büyük kareli ızgarası, köşede saniye. Küçük kareler hareket bulanıklığını yapay zekâ izi gibi gösteriyordu (gerçek yemek videosu %70 yapay zekâ çıktı)."""
    from PIL import Image, ImageDraw, ImageFont
    cikti = _klasor(cid)
    y = cikti / "izgara3" / f"{s['id']}.jpg"
    if y.exists():
        return [y]
    y.parent.mkdir(exist_ok=True)
    n = 9 if s["duration"] >= .6 else 4
    video = C.yol(cid) / "kaynak.mp4"
    kareler = []
    for i in range(n):
        t = s["start"] + (s["duration"] * (i + .5) / n)
        g = y.parent / f"_{s['id']}_{i}.jpg"
        subprocess.run([C.FFMPEG, "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale='if(gt(iw,ih),640,430)':-2", "-q:v", "3", str(g)], capture_output=True, timeout=30)
        if g.exists():
            kareler.append((t, g))
    if not kareler:
        return [cikti / s["assets"]["sheet"]]
    ilk = Image.open(kareler[0][1])
    w, h = ilk.size
    sut = 3 if n == 9 else 2
    sat = (len(kareler) + sut - 1) // sut
    tuval = Image.new("RGB", (w * sut, h * sat), (0, 0, 0))
    yazi = ImageFont.load_default(size=22)
    for i, (t, g) in enumerate(kareler):
        im = Image.open(g).convert("RGB").resize((w, h))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 92, 30), fill=(0, 0, 0))
        d.text((6, 3), f"{t:.2f}s", fill=(255, 220, 0), font=yazi)
        tuval.paste(im, ((i % sut) * w, (i // sut) * h))
        g.unlink()
    tuval.save(y, quality=82)
    return [y]


def gozden_gecir(cid, br):
    """Claude her çekime bakar; yanıtlar aracın kendi birleştirmesinden geçer (ölçüm + göz). Claude yoksa ölçümle kalır."""
    cikti = _klasor(cid)
    sira = _sec(br["shots"])
    cevap = {"by": "claude", "shots": []}
    d = C.oku(cid)
    ceviri = {}
    for i in range(0, len(sira), GRUP):
        grup = sira[i:i + GRUP]
        resim, etiket = [], []
        for s in grup:
            for x in _izgara(cid, s):
                if x.exists():
                    resim.append(str(x))
                    etiket.append(s["id"])
        if not resim:
            continue
        y = claude_yaz.json_coz(claude_yaz.sor_gorsel(GOZDEN.format(kunye=_kunye(d), liste=_liste(grup)) + ("\n\nKullanıcı İngilizce kullanıyor: evidence, description ve cekim alanlarını İngilizce yaz." if d.get("dil") == "en" else "") + "\n\nEkteki resimlerin sırası (bir çekimin birden çok ızgarası olabilir): " + ", ".join(etiket), resim, model_adi="opus"))
        for a in (y or {}).get("shots") or []:
            if isinstance(a, dict) and a.get("id"):
                ceviri[a["id"]] = {"cekim": str(a.get("cekim") or "")[:300], "kanit": [str(x)[:200] for x in (a.get("evidence") or [])[:3]], "ne": str(a.get("description") or "")[:300]}
                cevap["shots"].append(a)
    if not cevap["shots"]:
        return br, {}
    (cikti / "review_answers.json").write_text(json.dumps(cevap, ensure_ascii=False), encoding="utf-8")
    r = _rea("apply-review", str(cikti), str(cikti / "review_answers.json"), "--by", "claude", zaman=180)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "gözden geçirme birleştirilemedi")[-300:])
    return json.loads((cikti / "breakdown.json").read_text(encoding="utf-8")), ceviri


def _temiz_yazi(c, vision):
    m = (c.get("text") or "").strip()
    if len(m) < 2 or (CJK.search(m) and not CJK.search(vision)):
        return False
    return bool(re.search(r"[^\W\d_]{2}", m))


OLCULEN = {"static_hold", "still_motion"}       # pikselden kesin ölçülür
GORUNEN = {"live_action", "ai_video", "avatar", "cg_3d", "anim_2d", "stop_motion", "code_render", "screen_capture"}


def _karar(s):
    """Çekimin türü: ölçülebilen türlerde (donmuş kare, kayan fotoğraf) ölçüm; ötekilerde göz. Platform yeniden kodlaması ölçümü bozuyor: gerçek yemek videosunda araç çekimlerin %67'sine
    yapay zekâ dedi, aracın kendi birleştirmesi de doğru bakışı aşağı çekti. Bakılmamış çekimde yalnız ölçüm vardır ve güveni düşük sayılır. -> (tür, güven, ikinci, çelişki)"""
    det = (s.get("deterministic") or {}).get("probs") or {}
    d_sira = sorted(det.items(), key=lambda kv: -kv[1])
    goz = (s.get("review") or {}).get("raw_probs") or {}
    g_sira = sorted(goz.items(), key=lambda kv: -kv[1])
    if d_sira and d_sira[0][0] in OLCULEN and d_sira[0][1] >= .6:
        return d_sira[0][0], round(d_sira[0][1], 2), None, False
    if g_sira and g_sira[0][1] > 0:
        ik = next((a for a, x in g_sira[1:] if x >= .25), None)
        return g_sira[0][0], round(g_sira[0][1], 2), ik, g_sira[0][1] < .6
    b = s.get("base") or {}
    tur = b.get("label") or (d_sira[0][0] if d_sira else "live_action")
    return tur, round(min(float(b.get("confidence") or 0), .55), 2), next((a for a, x in d_sira if a != tur and x >= .2), None), True


def ozet(cid, br, goz=None):
    """Ham ölçümü ekranda ve istemde kullanılacak sade Türkçe biçime çevirir."""
    goz = goz or {}
    d = C.oku(cid)
    sahne = []
    for s in br["shots"]:
        tur, guven, yedek, supheli = _karar(s)
        rv = s.get("review") or {}
        rep = rv.get("replication") or {}
        g = goz.get(s["id"]) or {}
        sahne.append({"no": s.get("index") or 0, "id": s["id"], "bas": round(s["start"], 2), "bit": round(s["end"], 2), "tur": tur, "ad": TUR_AD.get(tur, tur),
                      "guven": guven, "ikinci": TUR_AD.get(yedek), "supheli": supheli, "ne": g.get("ne") or rv.get("description") or "", "kanit": g.get("kanit") or (rv.get("evidence") or [])[:3], "cekim": g.get("cekim") or "",
                      "islem": [{"ad": ISLEM_AD.get(e["kind"], e["kind"]), "kanit": e.get("evidence") or ""} for e in rv.get("ai_edits") or []],
                      "istem_en": (rep.get("video_prompt_en") or "") if tur in ("ai_video", "cg_3d", "avatar") else "", "gorsel_istem": (rep.get("image_prompt") or "") if tur in ("ai_video", "cg_3d", "avatar") else "", "bakildi": bool(rv),
                      "kare": (s.get("assets") or {}).get("sheet") or ""})
    sure = float((br.get("source") or {}).get("duration") or 0) or (sahne[-1]["bit"] if sahne else 0)
    dagilim = {}
    for x in sahne:
        dagilim[x["tur"]] = dagilim.get(x["tur"], 0) + (x["bit"] - x["bas"])
    karisim = [{"tur": a, "ad": TUR_AD.get(a, a), "oran": round(v / max(sure, .1), 3)} for a, v in sorted(dagilim.items(), key=lambda kv: -kv[1])]

    au, ss = br.get("audio") or {}, br.get("sound_sources") or {}
    mz, vo, sf = au.get("music") or {}, au.get("voice") or {}, au.get("sfx") or {}
    anahtar = mz.get("key") or {}

    def tahmin(alan, sozluk):
        p = sorted(((ss.get(alan) or {}).get("probs") or {}).items(), key=lambda kv: -kv[1])
        return sozluk.get(p[0][0]) if p and p[0][1] >= .4 else None
    plan = br.get("audio_plan") or {}
    efekt = [{"t": round(float(e.get("t") or 0), 1), "tur": e.get("type") or "", "bag": bool(e.get("on"))} for e in (plan.get("sfx_merged") or []) if e.get("confidence") != "low"]
    ses = {"var": bool(au.get("has_audio")), "konusma": {"var": bool(vo.get("present")), "sarki": bool(vo.get("sung")), "kaynak": tahmin("voice", SES_AD)},
           "muzik": {"var": bool(mz.get("present")), "bpm": mz.get("tempo_bpm") if (mz.get("beat_strength") or 0) >= .01 or mz.get("present") else None,
                     "anahtar": f"{anahtar.get('tonic')} {'minör' if anahtar.get('mode') == 'minor' else 'majör'}" if anahtar.get("tonic") and (anahtar.get("confidence") or 0) >= .6 else None,
                     "kaynak": tahmin("music", MUZIK_AD), "degisim": [round(float(x), 1) for x in (mz.get("section_changes") or [])[:6]]},
           "efekt": {"sayi": len(efekt), "liste": efekt[:12], "kaynak": tahmin("sfx", EFEKT_AD) if efekt else None},
           "kesme_vurus": bool(au.get("beat_synced_edit")),
           "ayrim": sorted(p.stem for p in (_klasor(cid) / "stems").glob("*.wav")) if (_klasor(cid) / "stems").exists() else []}

    pk = br.get("packaging") or {}
    vision = " ".join(y.get("metin") or "" for y in (d.get("tarif") or {}).get("yazilar") or [])
    yazilar = [c for c in pk.get("text_cues") or [] if _temiz_yazi(c, vision) and c.get("kind") != "scene"]
    tur_say = {}
    for c in yazilar:
        tur_say[c["kind"]] = tur_say.get(c["kind"], 0) + 1
    yazi = {"altyazi": tur_say.get("subtitle", 0), "vurgulu": tur_say.get("huazi", 0), "baslik": tur_say.get("title", 0), "etiket": tur_say.get("label", 0),
            "cikartma": len([x for x in pk.get("stickers") or [] if x.get("confidence") not in (None, "low")]),
            "ornek": [{"t": round(float(c.get("t0") or 0), 1), "metin": c["text"][:60], "tur": c["kind"], "stil": c.get("style_zh") or ""} for c in yazilar[:8]]}

    p = br.get("provenance") or {}
    ai = p.get("aigc") or {}
    h = p.get("hints") or {}
    temiz = lambda L: [x for x in (L or []) if not str(x).endswith("?")]
    izler = {"yapay_zeka_etiketi": ai.get("label") in ("1", "2", "3"), "uretici": temiz(h.get("generator")), "duzenleyici": temiz(h.get("editor")), "cizici": temiz(h.get("renderer")),
             "kamera": h.get("camera") or [], "c2pa": any(e.get("kind") == "c2pa" for e in p.get("evidence") or []),
             "yeniden_kodlanmis": bool((br.get("video_context") or {}).get("transcoded"))}
    plan_u = br.get("production_plan") or {}
    birim = [{"tur": u.get("label"), "ad": TUR_AD.get(u.get("label"), u.get("label_zh") or ""), "bas": u.get("start"), "bit": u.get("end"), "cekimler": u.get("shots") or [], "kez": u.get("calls") or 1} for u in plan_u.get("units") or []]
    say = (br.get("summary") or {})
    gecis = {"cut": "kesme", "dissolve": "geçişli kesme", "fade": "kararma", "wipe": "silme"}
    gecisler = {gecis.get(a, a): b for a, b in (say.get("transitions") or {}).items() if a != "start"}
    kam_ad = {"拉": "geri çekiliyor", "推": "yaklaşıyor", "摇": "dönüyor", "移": "kayıyor", "跟": "takip ediyor", "升": "yükseliyor", "降": "alçalıyor"}
    kamera = {}
    for r in br["shots"]:
        m = ((r.get("aspects") or {}).get("camera") or {}).get("measured") or {}
        n = kam_ad.get(m.get("move"))
        if n:
            kamera[n] = kamera.get(n, 0) + 1
    return {"arac": "rea-video", "gozle": bool(goz), "sure": round(sure, 2), "karisim": karisim, "sahneler": sahne, "ses": ses, "yazi": yazi, "izler": izler,
            "kurgu": {"gecisler": gecisler, "kamera": kamera, "ort_plan": say.get("avg_shot_s"), "kesme": max(0, len(sahne) - 1), "dakikada": round(max(0, len(sahne) - 1) / max(sure, 1) * 60, 1)}, "uretim": {"birim": birim, "kez": plan_u.get("calls"), "cekim": plan_u.get("shoot") and len(plan_u["shoot"])}}


def istem_metni(o):
    """Rehber isteminin ÖLÇÜM bölümü."""
    if not o:
        return "(sahne ölçümü yapılmadı)"
    L = ["Çekim çekim karar; no = çekim numarası (araç ölçtü" + (", görüntüye de bakıldı" if o.get("gozle") else "; görüntüye bakılmadı") + "):"]
    L += [f"- no {s['no']}, {s['bas']:.1f}-{s['bit']:.1f} sn: {s['ad']} %{round(s['guven'] * 100)}" + (f" (ikinci ihtimal {s['ikinci']})" if s.get("ikinci") else "") + (" [emin değil]" if s.get("supheli") else "")
          + (f"; {s['ne']}" if s.get("ne") else "") + ("; " + "; ".join(x["ad"] for x in s["islem"]) if s.get("islem") else "") + (f"; çekim: {s['cekim']}" if s.get("cekim") else "") for s in o["sahneler"][:40]]
    L.append("Karışım: " + ", ".join(f"{x['ad']} %{round(x['oran'] * 100)}" for x in o["karisim"]))
    s, z = o["ses"], o["izler"]
    m = s["muzik"]
    L.append(f"Ses: konuşma {'var' + (' (şarkı söyleniyor)' if s['konusma']['sarki'] else '') if s['konusma']['var'] else 'yok'}; müzik " + (f"var, {m.get('bpm')} BPM, {m.get('anahtar') or 'anahtar belirsiz'}" if m["var"] else "yok")
             + (f", {m['kaynak']}" if m.get("kaynak") else "") + f"; efekt {s['efekt']['sayi']}. (Sesin kaynağı yalnız tahmindir; şarkı adı başka yerden geldiyse ona güven.)")
    et = [a for a, b in (("dosyada yapay zekâ etiketi", z["yapay_zeka_etiketi"]), ("içerik kimlik bilgisi (C2PA)", z["c2pa"])) if b] + z["uretici"] + z["duzenleyici"] + z["cizici"] + z["kamera"]
    ku = o.get("kurgu") or {}
    L.append(f"Hareket ve geçiş: {ku.get('kesme', 0)} kesme, dakikada {ku.get('dakikada')}" + (", kesmeler müziğin vuruşuna oturuyor" if s.get("kesme_vurus") else "")
             + (f"; geçişler: {ku['gecisler']}" if ku.get("gecisler") else "") + (f"; kamera: {ku['kamera']}" if ku.get("kamera") else ""))
    if (o.get("yazi") or {}).get("ornek"):
        L.append("Üstteki yazı biçimi (ölçüldü, Çince yazılmış olabilir): " + " | ".join(f"{y['t']} sn '{y['metin']}' {y['stil']}" for y in o["yazi"]["ornek"][:5]))
    u = o.get("uretim") or {}
    if u.get("kez"):
        L.append(f"Bu çekimleri yapay zekâyla yeniden yapmak için yaklaşık {u['kez']} üretim gerekir (tek üretimde birkaç çekim yapabilen modele göre).")
    L.append("Dosya izleri: " + (", ".join(et) if et else "yok") + (" (platform yeniden kodlamış; izlerin yokluğu bir şey kanıtlamaz)" if z["yeniden_kodlanmis"] else ""))
    return "\n".join(L)


_MODEL_KOD = r"""
import glob, json, os, yaml, rea_video
k = os.path.join(os.path.dirname(rea_video.__file__), "capabilities", "models")
L = []
for f in ("video", "character"):
    for m in (yaml.safe_load(open(os.path.join(k, f + ".yaml"), encoding="utf-8")).get("models") or []):
        if m.get("status") in ("shutdown", "deprecated"):
            continue
        L.append({"ad": m.get("name"), "cikis": m.get("release"), "sn": ((m.get("limits") or {}).get("duration_s") or {}).get("max"), "ses": bool((m.get("audio") or {}).get("native")),
                  "yetenek": [x for x in m.get("primitives") or [] if x in ("video.reference_video", "video.edit_v2v", "motion.transfer", "avatar.audio_driven", "lipsync.redub", "video.multi_shot", "video.i2v_first_last")]})
print(json.dumps(L, ensure_ascii=False))
"""


def model_tablosu():
    """Araçların süre sınırı ve yetenekleri (rea-video'nun tarihli tablosu): 'hangi araç bunu yapabilir' sorusuna dayanak; bu videoda kullanıldığının kanıtı değildir."""
    yol = C.KOK / ".rea_modeller.json"
    if not yol.exists() and REA_PY.exists():
        try:
            r = subprocess.run([str(REA_PY), "-c", _MODEL_KOD], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
            json.loads(r.stdout)
            yol.write_text(r.stdout, encoding="utf-8")
        except Exception:  # noqa: BLE001
            return ""
    try:
        return "\n".join(f"- {m['ad']}: tek seferde en çok {m['sn'] or '?'} sn" + (", kendi sesiyle" if m["ses"] else "") + (f"; {', '.join(YETENEK.get(y, y) for y in m['yetenek'])}" if m["yetenek"] else "")
                         for m in json.loads(yol.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return ""


YETENEK = {"video.reference_video": "referans videodan hareket/kamera alır", "video.edit_v2v": "var olan videoyu değiştirir", "motion.transfer": "hareket aktarır", "avatar.audio_driven": "fotoğrafı sesle konuşturur",
           "lipsync.redub": "dudak uyumu yapar", "video.multi_shot": "tek üretimde birkaç çekim", "video.i2v_first_last": "ilk ve son kareden üretir"}


def karar_uygula(cid, y):
    """Ana inceleme bütün kanıtları (platform, web, öğreticiler) görerek bir çekimin türünü düzeltebilir; sahne haritası buna uyar."""
    karar = [k for k in (y or {}).get("cekim_karari") or [] if isinstance(k, dict) and k.get("tur") in TUR_AD]
    if not karar:
        return

    def f(d):
        o = d.get("olcum")
        if not o:
            return
        for k in karar:
            for s in o["sahneler"]:
                if s["no"] == k.get("no") or k.get("no") == "hepsi":
                    s.update(tur=k["tur"], ad=TUR_AD[k["tur"]], supheli=False, duzeltildi=str(k.get("neden") or "")[:300])
                    if k.get("istem_en"):
                        s["istem_en"] = str(k["istem_en"])
                    if k.get("guven") in ("yuksek", "orta"):
                        s["guven"] = {"yuksek": .9, "orta": .7}[k["guven"]]
                    if s["tur"] not in ("ai_video", "cg_3d", "avatar"):
                        s["istem_en"] = ""
                    if k.get("neden"):
                        s["kanit"] = [str(k["neden"])[:300]] + [x for x in s.get("kanit") or []][:1]
        sure = max(float(o.get("sure") or 0), .1)
        pay = {}
        for s in o["sahneler"]:
            pay[s["tur"]] = pay.get(s["tur"], 0) + s["bit"] - s["bas"]
        o["karisim"] = [{"tur": a, "ad": TUR_AD.get(a, a), "oran": round(v / sure, 3)} for a, v in sorted(pay.items(), key=lambda kv: -kv[1])]
    C.degistir(cid, f)


def stem_m4a(cid):
    """Ayrılmış sesleri tarayıcının çalabileceği m4a'ya çevirir (bir kez)."""
    k = _klasor(cid) / "stems"
    for ad in ("vocals", "music"):
        w, m = k / f"{ad}.wav", k / f"{ad}.m4a"
        if w.exists() and not m.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(w), "-c:a", "aac", "-b:a", "128k", str(m)], timeout=120, check=False)


def calistir(cid, log=None):
    """Ölç + gözden geçir + is.json'a yaz. Hata fırlatmaz: Content'in geri kalanı bunsuz da çalışır."""
    log = log or (lambda m: C.log(cid, m))
    if not hazir():
        return None
    try:
        log("Video sahne sahne ölçülüyor: kare izleri, gürültü, ses ayrımı")
        br = olc(cid)
        if not br:
            return None
        log(f"{len(br['shots'])} çekim ölçüldü; çekimlere tek tek bakılıyor")
        goz = {}
        try:
            br, goz = gozden_gecir(cid, br)
        except Exception as e:  # noqa: BLE001
            print(f"[content {cid}] çekimlere bakılamadı: {e}", flush=True)
        stem_m4a(cid)
        o = ozet(cid, br, goz)
        C.guncelle(cid, olcum=o)
        log("Sahne haritası çıkarıldı: " + ", ".join(f"{x['ad']} %{round(x['oran'] * 100)}" for x in o["karisim"][:3]))
        return o
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] sahne ölçümü yapılamadı: {e}", flush=True)
        log("Sahne ölçümü yapılamadı; incelemeye devam ediliyor")
        return None


if __name__ == "__main__":
    print(json.dumps(calistir(sys.argv[1], log=print), ensure_ascii=False, indent=1)[:6000])
