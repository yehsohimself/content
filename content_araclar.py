"""content_araclar.py - yapay zekâ video araçlarının izleri (araç tanıma defteri, 2026-10-29).

Her araç için videoda bırakabileceği izler: görünür filigran, tek seferde ürettiği klip süreleri, tipik çözünürlük ve kare hızı, ses,
hareket ya da görüntü işaretleri. İki kullanım:
1. `defter_metni()` incelemenin istemine girer: model filigranı, kare hızını ve süreleri neye bakacağını bilerek arar.
2. `olc(d)` videodan ölçülebilen izleri (çekim süreleri, çözünürlük, kare hızı, kesmesiz uzun plan) defterle karşılaştırır.
   Ölçüm yalnız ipucudur ("olası"); kesinlik için filigran, sayfa bilgisi ya da sahibin sözü gerekir.
Bilgiler 2026 sonu itibarıyla tipik değerlerdir; araçlar sürüm değiştirdikçe güncellenmeli (Doğru mu? dersleri de buraya bakmayı öğretir).
"""

DEFTER = [
    {"ad": "Veo 3 / 3.1 (Google)", "sureler": [8.0], "en_uzun": 8.0,
     "filigran": "Gemini uygulamasında sağ altta küçük 'Veo' yazısı; Flow ve API çıktılarında görünür filigran yok (görünmez SynthID var)",
     "kare": "24 kare/sn", "ses": "yerleşik ses, ortam sesi ve dudakla uyumlu konuşma",
     "isaret": "çekimler çoğu zaman tam 8 sn; uzatma ile birleştirilmiş klipler 8 sn'nin katları"},
    {"ad": "Sora 2 (OpenAI)", "sureler": [10.0, 15.0], "en_uzun": 25.0, "boyut": [(704, 1280), (1280, 704)],
     "filigran": "bulut simgesi ve 'Sora' yazısı; video boyunca köşeden köşeye yer değiştirir",
     "kare": "30 kare/sn", "ses": "yerleşik ses ve konuşma; 'cameo' ile gerçek kişilerin yüzü ve sesi",
     "isaret": "704x1280 ya da 1280x704 gibi standart dışı boyut; kurgulanmış videoda tek klip 10-15 sn"},
    {"ad": "Kling (Kuaishou)", "sureler": [5.0, 10.0], "en_uzun": 10.0,
     "filigran": "ücretsiz sürümde sağ altta 'Kling AI' logosu",
     "kare": "24 ya da 30 kare/sn", "ses": "yeni sürümlerde isteğe bağlı ses",
     "isaret": "Motion Control ile referans videodan hareket aktarma; çekimler 5 ya da 10 sn"},
    {"ad": "Hailuo (MiniMax)", "sureler": [6.0, 10.0], "en_uzun": 10.0,
     "filigran": "ücretsiz sürümde 'Hailuo AI' yazısı", "kare": "24-25 kare/sn", "ses": "sessiz ya da sonradan eklenmiş",
     "isaret": "çekimler 6 ya da 10 sn"},
    {"ad": "Seedance (ByteDance; CapCut ve Dreamina içinde)", "sureler": [5.0, 10.0], "en_uzun": 15.0,
     "filigran": "Dreamina ya da CapCut logosu veya 'AI generated' notu", "kare": "24 kare/sn", "ses": "2.0 sürümünde ses ve dudak uyumu",
     "isaret": "CapCut AI Lab ve Dreamina'daki yapay zekâ video özelliklerinin modeli; çoklu referansla karakter tutarlılığı"},
    {"ad": "Runway (Gen-4, Aleph, Act-Two)", "sureler": [5.0, 10.0], "en_uzun": 10.0,
     "filigran": "ücretsiz sürümde 'Runway' yazısı", "kare": "24 kare/sn", "ses": "sessiz",
     "isaret": "Aleph var olan bir videonun görünümünü değiştirir; Act-Two bir oyuncunun hareketini karaktere aktarır"},
    {"ad": "Pika", "sureler": [5.0, 10.0], "en_uzun": 10.0, "filigran": "ücretsiz sürümde 'Pika' yazısı", "kare": "24 kare/sn",
     "ses": "isteğe bağlı ses efekti", "isaret": "Pikaffects: nesneyi ezme, eritme, şişirme gibi hazır efektler"},
    {"ad": "Viggle", "sureler": [], "en_uzun": 0, "filigran": "ücretsiz sürümde 'Viggle' yazısı", "kare": "değişken",
     "ses": "orijinal müzik/ses korunur",
     "isaret": "bir referans videonun dansı/hareketi bir karaktere aktarılır; karakter çoğu zaman düz ya da yeşil zeminde, uzuvlar titrer, yüz sabit"},
    {"ad": "Wan (Alibaba, açık model)", "sureler": [5.0], "en_uzun": 5.0, "filigran": "yok (kendi bilgisayarında çalıştırılabilir)",
     "kare": "16 kare/sn (2.1) ya da 24 kare/sn (2.2)", "ses": "sessiz",
     "isaret": "Wan Animate ile var olan videoda karakter değiştirme; 16 kare/sn akıcılığı"},
    {"ad": "Konuşan avatar araçları (HeyGen, Synthesia, Hedra)", "sureler": [], "en_uzun": 0,
     "filigran": "ücretsiz sürümde araç adı", "kare": "25-30 kare/sn", "ses": "kusursuz dudak senkronu, düz ve temiz ses",
     "isaret": "sabit kadraj, gövde neredeyse hareketsiz, yalnız baş ve ağız oynar"},
    {"ad": "Meta AI (Vibes, Restyle)", "sureler": [], "en_uzun": 0,
     "filigran": "Instagram/Facebook'ta 'Yapay zeka ile oluşturuldu' ya da 'Imagined with AI' etiketi; ortak gönderen 'meta.ai'",
     "kare": "değişken", "ses": "orijinal ses", "isaret": "Restyle kullanıcının kendi videosunun görünümünü değiştirir"},
    {"ad": "Midjourney Video", "sureler": [5.0], "en_uzun": 21.0, "filigran": "yok", "kare": "24 kare/sn", "ses": "sessiz",
     "isaret": "480p ya da 720p; Midjourney görselinin canlandırılması, +4 sn uzatmalar"},
    {"ad": "CapCut şablonu", "sureler": [], "en_uzun": 0,
     "filigran": "TikTok sayfasında 'CapCut · Şablonu dene' bağlantısı; bitiş kartında CapCut logosu",
     "kare": "30 kare/sn", "ses": "şablonun müziği", "isaret": "kesmeler müziğin vuruşlarına oturur; aynı kurgu binlerce videoda tekrar eder"},
]

TOLERANS = 0.3            # sn; çekim süresi ölçüsü sahne tespitinin payıyla
UZUN_TEK_PLAN = 20.0      # sn; çoğu araç tek seferde 5-15 sn üretir


def defter_metni():
    return "\n".join(f"- {a['ad']}: filigran: {a['filigran']}; kare hızı: {a['kare']}; ses: {a['ses']}; "
                     + (f"tek klip: {' ya da '.join(f'{s:g}' for s in a['sureler'])} sn; " if a['sureler'] else "")
                     + f"işaret: {a['isaret']}" for a in DEFTER)


def olc(d):
    """Videodan ölçülebilen izler → [cümle]. Ölçüm ipucudur, kanıt değil."""
    k, t = d.get("kaynak") or {}, d.get("tarif") or {}
    w, h, fps, sure = int(k.get("w") or 0), int(k.get("h") or 0), float(k.get("fps") or 0), float(k.get("sure") or 0)
    sah = [round(float(s["bit"]) - float(s["bas"]), 2) for s in t.get("sahneler") or [] if s.get("bit") is not None]
    out = []
    if sah:
        out.append(f"Çekim süreleri (sn, sahne tespitiyle; ±{TOLERANS} sn pay): {', '.join(f'{x:g}' for x in sah[:30])}")
    for a in DEFTER:
        if (w, h) in a.get("boyut", []):
            out.append(f"Video boyutu {w}x{h}: {a['ad']} için tipik, standart dışı bir boyut (orta güçte ipucu).")
    sureye = {}
    for a in DEFTER:
        for s_ in a["sureler"]:
            sureye.setdefault(s_, []).append(a["ad"].split(" (")[0])
    for s_, adlar in sorted(sureye.items()):
        tam = [x for x in sah if abs(x - s_) <= TOLERANS]
        if len(tam) >= 2 or (len(sah) == 1 and tam):
            ortak = len(adlar) > 2
            out.append(f"{len(tam)} çekim tam {s_:g} sn: {', '.join(adlar)} tek seferde bu sürede klip üretir; "
                       + ("çok yaygın bir süre, zayıf ipucu." if ortak else "olası ipucu (kesilmiş klipler bu ölçüyü bozar)."))
    if sah and max(sah) >= UZUN_TEK_PLAN:
        out.append(f"{max(sah):.1f} sn kesmesiz bir plan var. Yapay zekâ araçlarının çoğu tek seferde 5-15 sn üretir; bu uzunlukta tek plan "
                   "baştan üretilmiş tek bir klipten çok gerçek bir çekim ya da VAR OLAN bir videonun dönüştürülmesi (hareket aktarma, "
                   "yüz/karakter değiştirme, görünüm değiştirme) olabilir.")
    elif len(sah) == 1 and 4 <= sure <= 16:
        out.append(f"Video tek plan ve {sure:.1f} sn: tek bir yapay zekâ klibi ya da kısa bir gerçek çekim olabilir.")
    if fps:
        if abs(fps - 16) < 0.5:
            out.append("Kare hızı 16/sn: açık kaynak Wan modelinin tipik kare hızı (olası ipucu).")
        elif abs(fps - 24) < 0.1 or abs(fps - 23.98) < 0.05:
            out.append("Kare hızı 24/sn: sinema ve birçok yapay zekâ aracının varsayılanı; tek başına bir şey söylemez.")
    return out
