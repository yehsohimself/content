"""content_yontem.py - videonun nasıl yapıldığını çözer ve 101 seviyesinde adım adım anlatır (2026-10-28).

Kullanıcı kararı: Content video üretmez (bulut üretim sonuçları kötüydü). Verilen videonun yapılış yöntemini (CapCut şablonu mu, hangi efekt,
hangi yapay zekâ aracı, nasıl çekilmiş) çözer ve sıfırdan başlayan biri için adım adım rehber yazar. "Yap" denirse Claude, sohbette
bilgisayar kullanımıyla bu adımları uygular; ürünün içine üretim yeteneği konmaz.

coz(cid): content.cozumle'nin çıkardığı tarif (sahneler, ses yazısı, ekran yazıları, kareler) + video açıklaması/etiketleri → Claude (opus, görsel)
→ is.json `yontem`.
"""
import html
import json
import re
from pathlib import Path

import content as C
import content_araclar as A
import content_dogrulama as D
import content_benzer as B
import content_kanit as K

ISTEM = """Bir video yapım uzmanısın. Aşağıdaki viral videonun NASIL YAPILDIĞINI çözeceksin ve bunu hiç video düzenlememiş birine
(101 seviyesi) adım adım anlatacaksın. Kullanıcı programlama bilmez; sade Türkçe, "siz" dili.

SAYFA KANITI (platformun kendi verisi; KESİNDİR, buna dayan): {sayfa}

VİDEO
Başlık/ilk satır: {baslik}
Hesap: {kanal}
Açıklama ve etiketler: {aciklama}
Süre: {sure:.1f} sn, {w}x{h}
Sahneler (kesmeler): {sahneler}
Konuşma/ses yazısı: {ses}
Ekrandaki yazılar: {yazilar}
Önceki görsel çözümleme: {ozet}
Dosya etiketleri (platformun indirdiği dosya; üretici uygulamanın izi çoğu zaman silinmiştir): {dosya}

ŞARKI (sırayla: platformun kendi şarkı bilgisi, sesten tanıma (Shazam), sözlerden tahmin; 'kaynak' alanı hangisi olduğunu söyler): {sarki}
WEB'DE AKIM (şarkı adı ve TikTok'un önerdiği aramalarla açık web araması; sayfaların söyledikleri, kaynaklarıyla. Akımın adı ve canlandırdığı gerçek an
için GÜÇLÜ kanıttır; satış sayfaları araç adını abartabilir. Bu video o akımın bir çeşitlemesi olabilir, sayfalar bu videoyu anlatmaz): {web}
REPLİKLERİN KAYNAĞI (konuşmanın parçaları web'de arandı; bulunduysa SESİN geldiği film/dizi): {replik}
ÖLÇÜLEN İZLER (videodan kodla ölçüldü: çekim süreleri, boyut, kare hızı, kesmesiz uzun plan; araç adı için yalnız İPUCUDUR, tek başına 'olası'dan
güçlü olamaz; filigran ya da sayfa bilgisiyle örtüşürse güçlenir): {olcum}
ARAÇ TANIMA DEFTERİ (her aracın videoda bıraktığı izler; filigranı karelerde bu tariflere göre ara, süre ve boyutu ölçülen izlerle karşılaştır):
{defter}
KÜTÜPHANEDE AYNI SES (kullanıcının daha önce çözdürdüğü, AYNI sesi taşıyan videolar; aynı ses çoğu zaman aynı akım demektir): {kutuphane}
BENZER VİDEOLAR (aynı şarkı/akım/şablon adıyla bulunup İNDİRİLİP ÖLÇÜLDÜ: ses zarfı benzerliği 0-1, görüntü parmak izi benzerliği 0-1;
ekte her biri için üst sıra bu video, alt sıra benzer video olmak üzere yan yana kare şeritleri var): {benzer}
Bunlardan yöntem okunur: ses AYNI + görüntü FARKLI = aynı sese/kalıba herkes kendi görüntüsünü koyuyor (şablon, akım, hareket aktarma, yüz değiştirme);
ses aynı + görüntü AYNI = birebir yeniden paylaşım ya da aynı kaynağın küçük bir düzenlemesi; ses farklı + görüntü çok benzer = aynı görüntüye yeni ses (dublaj,
seslendirme, replik değiştirme). Kopyalar arasında SABİT kalan şey şablon/akımdır, DEĞİŞEN şey yapanın kattığıdır.
KAYNAK TÜRÜ: {statik}

YORUMLAR (izleyicilerin; zayıf kanıt: şaka, reklam, yanlış bilgi olabilir; birden çok kişinin aynı şeyi söylemesi ve VİDEO SAHİBİ'nin
yanıtı daha değerlidir): {yorumlar}

Ekte videodan sırayla KARE IZGARALARI var: her ızgara bir sahnenin (ya da uzun sahnenin bir parçasının) sık aralıklı kareleri, soldan sağa,
yukarıdan aşağı; her karenin köşesinde "S<sahne no> · <saniye>s" yazar. Hareketi kareler ARASINDAKİ değişimden oku (kim nereye gidiyor, top/nesne
nereye gidiyor, kamera kayıyor mu). Ardından benzer videoların yan yana kare şeritleri ({serit} resim; üst sıra bu video, alt sıra benzer video). Son {uc} resim videonun İLK ANI ve SON 2 SANİYESİDİR:
köşelerde araç filigranı/logosu (CapCut, Kling, Hailuo, Sora, Vidu, Pika, Runway, Veo ✦, Meta AI, Remini…) ya da bitiş kartı ara;
görürsen kanıt olarak yaz. Filigran olmaması bir şey kanıtlamaz (ücretli sürüm ya da silinmiş olabilir).

KULLANICININ NOTU: "{istek}"
KULLANICININ DÜZELTMESİ (bu videonun gerçeği; kullanıcı daha önceki çözümü düzeltti, buna uy ve rehberi buna göre kur): {duzeltme}
GEÇMİŞ HATALARDAN DERSLER (kullanıcının başka videolarda düzelttiği hatalardan çıkan genel kurallar; uygunsa uygula): {dersler}

BUGÜNKÜ YAPAY ZEKÂ VİDEO MODELLERİ (sunra.ai kataloğu; yalnız bir yol önerirken GÜNCEL ad ve yeteneği doğru yazmak için başvuru;
bu videoda hangisinin kullanıldığına KANIT DEĞİL, kanıt yoksa adı 'örneğin' diye ver): {modeller}

İPUÇLARI: Açıklamada/etiketlerde "CapCut", "template", "şablon", "#capcuttemplate", "Use template" geçmesi, ekranda CapCut filigranı, birebir
aynı kurgunun binlerce videoda tekrarı → CapCut şablonu. Yüz/kişinin başka bir sahneye konması, yapay zekâ tarzı akıcı ama tuhaf hareket,
"AI" etiketi → yapay zekâ video aracı (ör. CapCut'ın kendi AI özellikleri, Kling, Hailuo, Pika, Viggle, Higgsfield, Runway); emin değilsen
adını uydurma, "yapay zekâ ile kişi değiştirme aracı (büyük olasılıkla …)" de. Telefon ekranı kaydı + kalem → anlatım videosu: o zaman
anlatılan YÖNTEMİ çöz (videonun kendisini değil, öğrettiğini). Eldeki kanıtı göster (hangi kare, hangi yazı).

KAYNAK KLİP: yapay zekâ akımlarının çoğu bilinen GERÇEK bir anın (ünlü gol, dans, film sahnesi) hareketini ve zamanlamasını koruyup karakterleri ve
dünyayı değiştirir (hareket aktarma: Kling Motion Control, CapCut AI Lab'deki referans videolu yapay zekâ videosu, Viggle, Runway Act gibi).
İşaretleri: eylem sahneye ait değil (ör. Men in Black karargâhında futbol topu sektirmek), kesmesiz 10-15 sn tek plan, akımın şarkısı, yapay zekâ
etiketi. Böyle görünüyorsa yöntemi buna göre çöz: orijinal klip ne (kütüphanede aynı ses varsa oradan; yoksa hareketten tahmin et, emin değilsen
söyle), nereden bulunur, hangi araca referans video olarak verilir, istem ne olmalı. Kaynak klip tahminin için 'kaynak_klip' doldur. Orijinal anı
MEKÂNA ya da KARAKTERLERE göre değil HAREKETE göre ara (dünya değiştirilmiştir): 'eylem' = hareketin İngilizce kısa adı (ör. "football goal
dribbling past defenders", "dance choreography", "skateboard trick").

SES İLE YÜZLER UYUŞMUYORSA (ör. Breaking Bad karakterleri Türkçe ve doğal oyuncu sesiyle konuşuyor): iki ihtimal var, ikisini de tart:
(a) görünen karakterlerin görüntüsüne YENİ ses konmuş (yapay zekâ seslendirme/dublaj, konuşan video modeli);
(b) sesin geldiği GERÇEK bir film/dizi sahnesi alınmış, ORİJİNAL SESİ korunmuş, yalnız yüzler/karakterler değiştirilmiş (yüz değiştirme, karakter
değiştirme: ör. Kling/Wan "character replace", Viggle, FaceFusion, DeepFaceLab); dudaklar zaten orijinal oyuncunun konuşmasını izler.
(b)'nin işaretleri: ses doğal oyuncu sesi (nefes, tonlama, ortam sesi, eski film kaydı, kısık bant), konuşma bir filmin akışından (adlar, yerler,
olay örgüsüne göndermeler; espri senaryosu gibi değil), sahnenin kompozisyonu ve mekânı görünen karakterlerin dizisinde YOK (dizinin bölümleriyle
eşleşmiyor), sahne uzun ve kesmesiz bir film planı, kıyafet/şapka/duman gibi ayrıntılar kareden kareye kayıyor. REPLİKLERİN KAYNAĞI bulunduysa (b)
neredeyse kesindir: 'kaynak_klip' o film sahnesidir. Bulunamadıysa ve işaretler (b)'yi gösteriyorsa (b)'yi ana yol yaz, kaynak_klip.ne = "sesin geldiği
film/dizi sahnesi (adı bulunamadı)", arama = repliklerden 1-2 arama; (a)'yı emin_olmadiklarim'a koy. Yalnız ses açıkça yapay/temiz ve konuşma kısa bir
espri senaryosuysa (a)'yı seç.

SAYFA KANITINDA şablon bağlantısı (ör. "CapCut · Try this template", template_id, şablon adı/kullanım sayısı) varsa yöntem kesindir: guven
'yuksek', şablonun adını ve bağlantısını ver. Şablon bağlantısı YOKSA şablon iddiasını yalnız güçlü görsel/açıklama kanıtıyla yap.

ADIMLAR: gerçek uygulama menü adlarıyla (CapCut Türkçe arayüzde "Şablonlar", "Şablonu kullan", "Dışa aktar"; İngilizcesini parantezle),
her adım tek iş; telefon mu bilgisayar mı belirt; şablon varsa nasıl bulunacağını (TikTok'ta videonun altındaki "CapCut · Şablonu dene"
bağlantısı, CapCut'ta arama sözcüğü) yaz. Ücretli/üyelik isteyen adımı açıkça söyle. Uydurma düğme adı yazma; emin değilsen "… gibi bir düğme".

ÖNCE HAREKET, SONRA YORUM: görünüş (kostüm, mekân, karakter) yapay zekâyla tamamen değiştirilmiş olabilir; ilk yorumu ona dayandırma. JSON'daki
ilk alan 'hareket_tutanagi': sahne sahne, OLAY ADI, kişi adı, marka ya da mekân adı KOYMADAN yalnız fiziksel hareketi yaz (ör. "S1: bir figür topla
soldan sağa koşuyor, iki figür ayakları önde yere kayıyor, figür öne çıkıyor, top iki direk arasından geçiyor; kamera sağa kayıyor"). Olayın ne
olduğunu (gol, dans, film sahnesi) ancak bundan sonra, ozet ve kaynak_klip alanlarında söyle.

ARAÇ KANITI: her araç için 'dayanak' yaz, en güçlü kanıt türünü seç: platform (sayfa kanıtında bağlantı/etiket), sahip (video sahibi açıklamada ya
da yorum yanıtında söylüyor), dosya (dosya etiketinde), logo (karede görünür filigran/logo; hangi resimde), ogretici (öğretici video adlandırıyor),
web (web'deki akım sayfaları adlandırıyor), yorum (izleyiciler söylüyor), reklam (sahip bir aracı ortaklık/indirim linkiyle ÖNERİYOR ama bu
videonun onunla yapıldığını söylemiyor; 'sahip' DEĞİLDİR), olcum (ÖLÇÜLEN İZLER'deki süre/boyut ipucu), gorsel (yalnız görüntüden izlenim). Yalnız görüntüden model adı söylemek
güvenilir DEĞİL (güncel modellerde dedektörler bile yazı turaya yakın): dayanak gorsel ise adı "örneğin" diye ver, kesin deme.

JSON döndür:
{{
 "hareket_tutanagi": ["S1: …", "S2: …"],
 "baslik": "nasıl yapıldığını 3-7 kelimeyle söyleyen sade başlık, teknik terim yok (ör. 'Film sahnesine yapay zekâyla yeni yüzler', 'Hazır CapCut şablonu ve bir fotoğraf')",
 "ozet": "bu video nasıl yapılmış, 1-2 cümle",
 "yontem": "capcut_sablon | capcut_elle | yapay_zeka_araci | cekim_kurgu | ekran_kaydi | karisik",
 "guven": "yuksek | orta | dusuk",
 "kanit": ["neye bakarak bu sonuca vardın, kısa maddeler"],
 "araclar": [{{"ad": "KISA ad, en çok 4 kelime (ör. 'Yapay zekâ video aracı', 'CapCut'); parantez ve örnek listesi YOK; YALNIZ uygulama/araç/hizmet (film klipleri, fotoğraf, şarkı gibi MALZEME araç değildir, onlar 'gerekenler'e)", "ornek": "kanıt yoksa örnek araçlar, yalnız adlar, kısa (ör. 'Kling, Dreamina ya da Wan'; başına 'örneğin' yazma) ya da boş", "ne_icin": "bu videoda ne işe yaradı", "ucret": "ücretsiz | ücretli | bir kısmı ücretli", "dayanak": "platform | sahip | dosya | logo | ogretici | web | yorum | reklam | olcum | gorsel"}}],
 "sablon": {{"var": true, "ad": "şablonun adı (sayfa kanıtında varsa)", "link": "şablon bağlantısı (yalnız sayfa kanıtında varsa)", "nasil_bulunur": "…", "arama": "CapCut'ta aranacak sözcük ya da boş"}},
 "claude_yolu": {{"mumkun": true, "neden": "tek cümle: Claude bu işi Mac'te (tarayıcı ya da masaüstü uygulaması) yapabilir mi, neden", "adimlar": [{{"baslik": "kısa", "ne_yapilir": "Claude'un Mac'te yapacağı iş; kullanıcıdan gereken (fotoğraf dosyası, giriş) varsa söyle"}}]}}
   (Telefona özgü bir uygulama/özellik gerekiyorsa mumkun false ve adimlar boş; şablonun web sayfası ya da masaüstü uygulamasında karşılığı
   olduğundan emin değilsen mumkun false; uydurma),
 "gerekenler": ["başlamadan hazır olması gerekenler: telefon, fotoğraf (nasıl), video, hesap…"],
 "sema": [{{"ad": "1-3 kelime", "alt": "en çok 6 kelime"}}] (3-6 düğüm: girdi → araç/işlem → sonuç; videonun yapılışını tek bakışta anlatan akış),
 "yapilacaklar": ["en çok 6 kısa madde: kullanıcının hazırlaması/yapması gereken somut işler (ör. 'Boydan, düz arka planlı 1 fotoğraf çekin')"],
 "adimlar": [{{"baslik": "kısa", "nerede": "Uygulama › menü › düğme", "ne_yapilir": "1-3 cümle, 101 seviyesinde", "ipucu": "isteğe bağlı",
   "kim": "claude | siz" (claude = Claude bilgisayarda ekranı görerek yapabilir; fotoğraf çekmek, telefonda dokunmak, giriş yapmak, ödeme = siz)}}],
 "sure": "yaklaşık kaç dakika sürer",
 "zorluk": "kolay | orta | zor",
 "sik_hatalar": ["en çok 3"],
 "sizin_icin": "kullanıcının notuna (varsa) göre nasıl uyarlanır; not yoksa boş",
 "emin_olmadiklarim": ["kesin bilmediğin noktalar; uydurma yapma"],
 "degisen_katmanlar": {{"kaynak": "video | fotograf | yapay (sıfırdan üretilmiş) | ekran_kaydi", "kisiler": "aynen | degistirilmis | eklenmis | yok", "ses": "ozgun (görüntünün kendi sesi) | sarki | dublaj (görüntüye sonradan konuşma/ses) | sessiz", "ortam": "aynen | degistirilmis | yapay", "hareket": "ozgun | aktarilmis (başka bir anın hareketi) | durağan", "ozet": "tek cümle: bu videoda ne değiştirilmiş, ne aynen kalmış"}},
 "kaynak_klip": {{"olasi": true, "ne": "orijinal an, ör. 'Mesut Özil'in Ludogorets'e attığı gol' ya da boş", "neden": "kısa", "eylem": "videodaki ana fiziksel hareketin İngilizce kısa adı; HER ZAMAN doldur (olasi false olsa da)", "arama": ["YouTube'da orijinal anı bulacak 1-2 arama (harekete göre)"]}},
 "ogretici_aramalari": ["YouTube'da bu videonun aynısını yapmayı öğreten videoyu bulacak 2-3 arama: akımın/şablonun/efektin adı + 'tutorial' ya da 'how to'; biri İngilizce, biri videonun dilinde"]
}}"""


DENETIM = """Aşağıda bir videonun nasıl yapıldığına dair taslak bir çözümleme var. Görevin onu DOĞRULUK için denetlemek; kullanıcı bu
adımları birebir uygulayacak, yanlış bir düğme adı ya da uydurma bir araç onu yolda bırakır.

KANIT (videodan): {kanit}

ÖĞRETİCİ VİDEOLAR (başkalarının bu videoyu/akımı nasıl yaptığını anlatan YouTube videoları; konuşma metni ve açıklaması):
{ogretici}

KAYNAK KLİP ADAYLARI (videonun hareketi bilinen gerçek bir andan aktarılmış olabilir; YouTube'da bulunan orijinal an adayları):
{kaynak}

BENZER VİDEOLAR (ölçülmüş; ekte yan yana şerit varsa ilk benzer video için): {benzer}

TASLAK: {taslak}

Kurallar:
- Kanıtta (açıklama, etiketler, ekran yazıları, ses, kareler) dayanağı olmayan araç/şablon iddiasını çıkar ya da 'kesin: false' yap.
- Gerçek uygulamalarda bulunduğundan emin olmadığın menü/düğme adını genelleştir ("sağ alttaki dışa aktarma düğmesi") ya da emin değilsen
  adımın 'emin' alanını false yap. Uygulama arayüzlerini bildiğin kadarıyla düzelt (CapCut, TikTok, Instagram).
- Adım sırası mantıklı ve eksiksiz olmalı: kurulum/giriş, girdi hazırlığı, asıl işlem, dışa aktarma, paylaşım. Eksik adımı ekle.
- SAYFA KANITI (platform verisi) kesindir: şablon bağlantısı varsa onu koru, şablonun adını/bağlantısını sil(me). Şablon bilgisinde
  'fotograf_video_yeri' kaç fotoğraf/video koyulacağını, 'sure_sn' süresini söyler; gerekenlere ve adımlara bunu yaz.
- ÖĞRETİCİ VİDEOLAR aynı akımı/efekti anlatıyorsa adımlar, menü adları, model/ayar seçimleri (ör. süre, oran, kredi, istem metni) için EN
  GÜÇLÜ kaynaktır: taslağı onlara göre düzelt; aynı videonun iki yolu varsa (ör. hazır şablon ve uygulamanın yapay zekâ bölümü) ikisini de
  söyle, kısa olanı ana yol yap. Konuşma metni otomatik altyazıdır, yanlış duyulmuş ad olabilir (ör. bir model adı); emin değilsen bunu
  emin_olmadiklarim'a yaz. Öğretici açıklamasında hazır istem (prompt) varsa aynen ver. İlgisizse yok say. Kullandığın öğreticileri
  'kaynaklar' listesine koy.
- KAYNAK KLİP: kanıttaki "KÜTÜPHANEDE AYNI SES" eşleşmesi güçlü kanıttır (aynı şarkı = çoğu zaman aynı akım); o videonun çözümünü dikkate al.
  Kaynak klip adayının küçük resmi videonun hareketine/kompozisyonuna (oyuncunun duruşu, topun yeri, kamera açısı) uyuyorsa 'kaynak_klip'e
  ne/link yaz ve yöntemi buna göre kur (orijinal klibi bulmak/indirmek, hareket aktaran araca referans video vermek, yeni karakter/dünya istemi).
  Uymuyorsa aday kullanma. Kaynak klipten emin değilsen 'kaynak_klip.kesin' false ve emin_olmadiklarim'a yaz.
- CapCut masaüstü uygulamasında şablon kütüphanesi YOK; ücretli şablonlar yalnız telefonda; bazı şablonlar web'de (capcut.com) açılır ama
  'web_sitesinde_kullanilabilir': false ise bu bölgede web'de kullanılamaz. Şablon yolu çoğu zaman telefon işidir.
- 'claude_yolu': Claude yalnız Mac'te ekranı görerek çalışır (tarayıcı, masaüstü uygulamaları); telefona dokunamaz. Bilgisayarda gerçekten
  yapılabileceğinden emin değilsen mumkun false yap ve nedenini sade yaz.
- REPLİKLERİN KAYNAĞI bulunduysa ses o filmdendir: görüntü o filmin sahnesinin yüz/karakter değiştirilmiş hali; 'kaynak_klip'i ona göre kur.
  Ses görünen karakterlere uymuyorsa (dil, ses tonu) ve yöntem "karakterlere yeni ses konmuş" diyorsa, "film sahnesine yeni yüz" ihtimalini yeniden tart.
- WEB'DE AKIM (kanıtta) akımın adını ve canlandırdığı gerçek anı söylüyorsa kaynak_klip'i ona göre kur; bu video çeşitleme olabilir, uydurma bağ kurma.
- Her aracın 'dayanak' alanını koru ya da düzelt (platform | sahip | dosya | logo | ogretici | web | yorum | reklam | olcum | gorsel); sahibin
  ortaklık/indirim linkiyle önerdiği araç 'reklam'dır, 'sahip' değil (videonun onunla yapıldığını söylemedikçe); öğretici ya da web bir aracı
  adlandırdıysa dayanağı ogretici/web yap. Yalnız görüntüye dayanan model adını "örneğin" diye ver.
- 'hareket_tutanagi'nı koru; karelerle çelişen satırı düzelt.
- 'degisen_katmanlar' (kaynak, kişiler, ses, ortam, hareket) kanıtla tutarlı olsun: BENZER VİDEOLAR ölçümü 'ses aynı, görüntü farklı' diyorsa kişiler/ortam değiştirilmiş demektir; 'ses farklı, görüntü benzer' diyorsa ses sonradan konmuştur. Fotoğraf gönderisinde hareket 'durağan'.
- 'baslik' (3-7 kelime, sade) ve araçların KISA 'ad' + 'ornek' biçimini koru; uzun araç adını kısalt, örnekleri 'ornek'e taşı. Adımlar sıradan
  bir telefon kullanıcısının anlayacağı dilde: teknik terim yok, her adım tek iş, düğme adı ekranda görüneceği gibi.
- 'guven': yalnız açık kanıt (ör. açıklamada 'CapCut template', ekranda şablon bağlantısı) varsa 'yuksek'.
- Metinler sade Türkçe, "siz" dili, kısa ve net; jargon yok. Şema 3-6 düğüm, her düğüm 1-3 kelime.
Aynı JSON şemasıyla düzeltilmiş tam çözümlemeyi döndür; her adıma "emin": true/false ekle, "kaynaklar": [{{"baslik": "öğretici başlığı", "link": "…",
"ne_aldin": "bu öğreticiden hangi bilgiyi aldın, kısa"}}], "kaynak_klip": {{"olasi": true, "ne": "orijinal an", "link": "yalnız adaylardan", "kesin": false,
"neden": "neye bakarak, kısa"}} ve "denetim_notu": "neyi değiştirdin, tek cümle"."""


UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}


def sayfa_kaniti(link):
    """Platformun sayfasındaki kesin bilgiler: TikTok'ta şablon bağlantısı (anchors), müzik, efektler, yapay zekâ etiketi; şablon sayfasından ad ve
    kullanım sayısı. Yalnız herkese açık sayfa okunur; hata olursa boş."""
    import requests
    k = {}
    try:
        if "tiktok.com" in link:
            t = requests.get(link, headers=UA, timeout=20).text
            m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', t, re.S)
            it = (json.loads(m.group(1)).get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {}).get("itemInfo", {}).get("itemStruct", {})) if m else {}
            for a in it.get("anchors") or []:
                ek = {}
                try:
                    ek = json.loads(a.get("logExtra") or "{}")
                except Exception:  # noqa: BLE001
                    pass
                k.setdefault("baglantilar", []).append({"yazi": a.get("keyword"), "tur": ek.get("anchor_type") or a.get("type"), "link": (a.get("schema") or "").split("?")[0],
                                                       "sablon_id": ek.get("template_id"), "ucretli": bool(ek.get("cc_template_pay_type"))})
            mu = it.get("music") or {}
            if mu:
                k["muzik"] = {"ad": mu.get("title"), "sahibi": mu.get("authorName"), "ozgun_ses": mu.get("original"), "kimlik": mu.get("id"),
                              "ses_dosyasi": mu.get("playUrl") or ""}      # özgün ses dosyası: content_benzer videonun sesiyle karşılaştırır
            ef = [e.get("name") for e in it.get("effectStickers") or [] if e.get("name")]
            if ef:
                k["efektler"] = ef
            if it.get("IsAigc") or it.get("AIGCDescription"):
                k["yapay_zeka_etiketi"] = it.get("AIGCDescription") or True
            if it.get("desc"):
                k["aciklama"] = it["desc"][:600]
            if it.get("creatorAIComment"):
                k["yapay_zeka_notu"] = str(it["creatorAIComment"])[:200]
            oneri = [w.get("word") if isinstance(w, dict) else w for w in (it.get("suggestedWords") or [])]
            if [w for w in oneri if w]:
                k["tiktok_onerilen_aramalar"] = [w for w in oneri if w][:8]
            yaz = [x for st in it.get("stickersOnItem") or [] for x in (st.get("stickerText") or [])]
            if yaz:
                k["yazi_cikartmalari"] = yaz[:10]
            if it.get("duetDisplay") or it.get("stitchDisplay") or it.get("originalItem"):
                k["duet_stitch"] = True
            k["_yazar_uid"] = (it.get("author") or {}).get("id")
            try:
                k.update(K.tiktok_ek(it))
            except Exception:  # noqa: BLE001
                pass
        for b in k.get("baglantilar") or []:
            if b.get("sablon_id") and "template-detail" not in (b.get("link") or ""):   # bağlantı bazen genel "editor-template" sayfasına gider;
                b["link"] = f"https://www.capcut.com/template-detail/{b['sablon_id']}"     # şablonun kendi sayfası adını ve kaç fotoğraf istediğini verir
            if "capcut.com/template" in (b.get("link") or ""):
                t = requests.get(b["link"], headers=UA, timeout=20).text
                m = re.search(r'property="og:description" content="([^"]*)"', t) or re.search(r'name="description" content="([^"]*)"', t)
                if m:
                    b["sablon_sayfasi"] = html.unescape(m.group(1))[:300]
                m = re.search(r'id="__MODERN_ROUTER_DATA__"[^>]*>(.*?)</script>', t, re.S)
                try:
                    td = json.loads(m.group(1))["loaderData"]["template-detail_$"]["templateDetail"] if m else {}
                except Exception:  # noqa: BLE001
                    td = {}
                if td:
                    b["sablon"] = {"ad": td.get("title"), "aciklama": (td.get("desc") or "")[:200], "yapan": (td.get("author") or {}).get("name"),
                                   "fotograf_video_yeri": td.get("segmentAmount"), "sure_sn": round((td.get("templateDuration") or 0) / 1000, 1),
                                   "kullanim": td.get("usageAmount"), "oran": td.get("videoRatio"),
                                   "ozellikler": td.get("capabilityName"),
                                   "web_sitesinde_kullanilabilir": td.get("useAvailable")}
    except Exception as e:  # noqa: BLE001
        k["hata"] = str(e)[:120]
    return k


YORUM_SORU = re.compile(r"how|nas[ıi]l|cara|c[oó]mo|wie |app|template|şablon|sablon|prompt|tutorial|\bai\b|\bia\b|\bki\b|song|şarkı|music|filter|efek|effect", re.I)


def yorumlar(link, n=30, yazar_uid=None):
    """TikTok'ta herkese açık yorumlar (giriş yok): en beğenilen n yorum + 'nasıl yapıldı / hangi uygulama / şarkı' sorularına gelen yanıtlar.
    Zayıf kanıttır (reklam/şaka olabilir); çözümleme bunu bilerek kullanır."""
    import requests
    m = re.search(r"/video/(\d+)", link or "")
    if "tiktok.com" not in (link or "") or not m:
        return []
    vid, h = m.group(1), dict(UA, Referer="https://www.tiktok.com/")
    try:
        j = requests.get(f"https://www.tiktok.com/api/comment/list/?aid=1988&aweme_id={vid}&count=50&cursor=0", headers=h, timeout=20).json()
    except Exception:  # noqa: BLE001
        return []
    cs = [c for c in j.get("comments") or [] if (c.get("text") or "").strip()]
    cs.sort(key=lambda c: -(c.get("digg_count") or 0))
    out, sorulan = [], 0
    for c in cs[:n]:
        y = {"metin": c["text"][:200], "begeni": c.get("digg_count") or 0}
        if yazar_uid and (c.get("user") or {}).get("uid") == yazar_uid:
            y["video_sahibi"] = True
        if c.get("is_author_digged"):
            y["video_sahibi_begendi"] = True
        if sorulan < 6 and c.get("reply_comment_total") and YORUM_SORU.search(c["text"]):
            sorulan += 1
            try:
                r = requests.get(f"https://www.tiktok.com/api/comment/list/reply/?aid=1988&item_id={vid}&comment_id={c['cid']}&count=20&cursor=0",
                                 headers=h, timeout=20).json()
                y["yanitlar"] = [("(VİDEO SAHİBİ) " if yazar_uid and (x.get("user") or {}).get("uid") == yazar_uid else "") + x["text"][:160]
                                 for x in (r.get("comments") or [])[:8] if (x.get("text") or "").strip()]
            except Exception:  # noqa: BLE001
                pass
        out.append(y)
    return out


def _vtt_metin(yol):
    s = []
    for l in Path(yol).read_text(encoding="utf-8", errors="ignore").splitlines():
        l = re.sub(r"<[^>]+>", "", l).strip()
        if not l or "-->" in l or l.startswith(("WEBVTT", "Kind:", "Language:")) or l.isdigit():
            continue
        if not s or s[-1] != l:
            s.append(l)
    return " ".join(s)


def _kelimeler(s):
    return re.findall(r"[a-zçğıöşüéèêëàâäîïôöûüœñß]+", (s or "").lower())


def kutuphane_eslesme(cid):
    """Aynı sesi (şarkı ya da konuşma) kullanan, daha önce çözülmüş Content çalışmaları. Akımlar aynı sesle yayılır: 28 Ekim'de Men in Black
    görüntülü video, önceden çözülmüş Özil gol videosuyla aynı şarkıyı taşıyordu. Ses yazısı kelime kelime karşılaştırılır (otomatik yazı her seferinde
    biraz farklı çıkar; ortak kelime / kısa olanın kelimesi ≥ 0,5)."""
    import difflib
    d = C.oku(cid)
    a = _kelimeler((d.get("tarif") or {}).get("ses_yazisi"))
    if len(a) < 8:
        return []
    out = []
    for x in C.liste(200):
        if x.get("id") in (cid, d.get("test_kaynak")):
            continue
        if d.get("test") and (C.oku(x["id"]) or {}).get("link") == d.get("link"):   # denemede aynı videonun eski çözümü cevabı söylerdi
            continue
        try:
            o = C.oku(x["id"])
        except Exception:  # noqa: BLE001
            continue
        b = _kelimeler((o.get("tarif") or {}).get("ses_yazisi"))
        if len(b) < 8:
            continue
        ortak = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
        oran = ortak / min(len(a), len(b))
        if oran < 0.5:
            continue
        y, sk = o.get("yontem") or {}, o.get("sayfa_kaniti") or {}
        out.append({"id": x["id"], "oran": round(oran, 2), "link": o.get("link"), "ne": ((o.get("tarif") or {}).get("ozet") or "")[:400],
                    "yontem": (y.get("ozet") or "")[:400], "sablon": [b.get("sablon") or b.get("sablon_sayfasi") for b in sk.get("baglantilar") or []][:1],
                    "aciklama": ((o.get("kaynak") or {}).get("baslik") or "")[:200]})
    out.sort(key=lambda z: -z["oran"])
    return out[:3]


SARKI = """Bir videonun sesinden yazıya dökülen sözler: "{soz}"
Bu sözlerle YouTube'da aranınca şu başlıklar çıktı:
{liste}
Bu bir şarkı mı? Öyleyse adını ve sanatçısını başlıklardan çıkar (TikTok'ta yayılan sürümü/remiksi varsa onu da yaz). Konuşmaysa ya da başlıklar
uyuşmuyorsa sarki boş. Uydurma. JSON: {{"sarki": "ad", "sanatci": "…", "surum": "ör. TikTok remix ya da boş"}}"""


def sarki_bul(soz):
    """Videodaki şarkının adı: platform 'özgün ses' dediğinde sözlerle YouTube'da aranır, Claude (sonnet) başlıklardan adı çıkarır.
    Şarkı akımın imzasıdır; adıyla akımın kaynağı ve öğreticileri aranır."""
    import subprocess
    import claude_yaz
    k = _kelimeler(soz)
    if len(k) < 6:
        return {}
    try:
        r = subprocess.run([C.YTDLP, "--flat-playlist", "--no-warnings", "--print", "%(title)s", f"ytsearch6:{' '.join(k[:14])}"],
                           capture_output=True, text=True, timeout=60)
        y = claude_yaz.json_coz(claude_yaz.sor(SARKI.format(soz=" ".join(k[:40]), liste=r.stdout.strip()[:1200]), model_adi="sonnet")) or {}
    except Exception:  # noqa: BLE001
        return {}
    return y if (y.get("sarki") or "").strip() else {}


SECIM = """Bir viral videonun nasıl yapıldığını bulmaya çalışıyoruz. Video hakkında bilinenler:
{ozet}

YouTube'da şu sonuçlar çıktı (no | başlık | kanal | süre sn | izlenme):
{liste}

Görev iki liste:
1) "secilen": bu videonun AYNISINI ya da aynı akımı/efekti yapmayı adım adım öğreten (tutorial) en çok 3 sonuç. Yalnız aynı akım/efekt/şablon
   için olanları al; genel 'video düzenleme' ya da ilgisiz videoları alma.
2) "kaynak": video, gerçek ve bilinen bir anın (ünlü gol, dans, film sahnesi) hareketinin yapay zekâyla başka karakterlere/dünyaya taşınmış hali
   olabilir. O ORİJİNAL anı gösteren en çok 2 sonuç (ör. "The Perfect Goal - Mesut Özil vs Ludogorets"); emin olmasan da aday olarak koy, sonra
   görüntüyle karşılaştırılacak.
Hiçbiri uymuyorsa boş liste. JSON: {{"secilen": [no, ...], "kaynak": [no, ...]}}"""


def ogreticiler(cid, sorgular, ozet):
    """Videonun yapılışını anlatan başkalarının öğretici videoları: YouTube araması → Claude (sonnet) aynı akımı öğretenleri seçer → her birinin
    açıklaması (istemler/bağlantılar çoğu zaman orada) ve konuşma metni (otomatik altyazı). En güçlü 'nasıl yapılır' kanıtı."""
    import subprocess
    import claude_yaz
    aday, gor = [], set()
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", (C.oku(cid) or {}).get("link") or "")
    if m:
        gor.add(m.group(1))                 # videonun kendisi öğretici sayılmaz (kanıt saklanan denemede başlığı cevabı söylerdi)
    for q in list(dict.fromkeys(x for x in (sorgular or []) if x))[:6]:
        try:
            r = subprocess.run([C.YTDLP, "--flat-playlist", "--no-warnings", "--print", "%(id)s\t%(title)s\t%(channel)s\t%(duration)s\t%(view_count)s",
                                f"ytsearch8:{q}"], capture_output=True, text=True, timeout=90)
        except Exception:  # noqa: BLE001
            continue
        for l in r.stdout.splitlines():
            p = l.split("\t")
            if len(p) < 5 or p[0] in gor:
                continue
            try:
                sure = float(p[3])
            except ValueError:
                sure = 0
            if not 8 <= sure <= 1500:
                continue
            gor.add(p[0])
            aday.append({"id": p[0], "baslik": p[1], "kanal": p[2], "sure": int(sure), "izlenme": p[4]})
    if not aday:
        return [], []
    liste = "\n".join(f"{i} | {a['baslik']} | {a['kanal']} | {a['sure']} | {a['izlenme']}" for i, a in enumerate(aday))
    try:
        j = claude_yaz.json_coz(claude_yaz.sor(SECIM.format(ozet=ozet[:1800], liste=liste), model_adi="sonnet")) or {}
        sec, kay = j.get("secilen") or [], j.get("kaynak") or []
    except Exception:  # noqa: BLE001
        sec, kay = list(range(min(2, len(aday)))), []
    secilen = [aday[i] for i in sec if isinstance(i, int) and 0 <= i < len(aday)][:3]
    kaynaklar = [dict(aday[i], link=f"https://www.youtube.com/watch?v={aday[i]['id']}") for i in kay
                 if isinstance(i, int) and 0 <= i < len(aday) and aday[i] not in secilen][:2]
    klasor = C.yol(cid) / "is_ara" / "ogretici"
    klasor.mkdir(parents=True, exist_ok=True)
    out = []
    for a in secilen:
        url = f"https://www.youtube.com/watch?v={a['id']}"
        try:
            subprocess.run([C.YTDLP, "--skip-download", "--no-warnings", "-q", "--write-info-json", "--write-auto-subs", "--write-subs",
                            "--sub-langs", "en-orig,tr-orig,.*-orig,en,tr", "--sub-format", "vtt", "--sleep-subtitles", "2",
                            "-o", str(klasor / "%(id)s.%(ext)s"), url], capture_output=True, text=True, timeout=120)
        except Exception:  # noqa: BLE001
            pass
        aciklama, metin = "", ""
        try:
            aciklama = (json.loads((klasor / f"{a['id']}.info.json").read_text(encoding="utf-8")).get("description") or "")[:1500]
        except Exception:  # noqa: BLE001
            pass
        vtt = sorted(klasor.glob(f"{a['id']}.*.vtt"), key=lambda x: ("orig" not in x.name, x.name))
        if vtt:
            metin = _vtt_metin(vtt[0])[:5000]
        if aciklama or metin:
            out.append(dict(a, link=url, aciklama=aciklama, metin=metin))
    for a in kaynaklar:                                            # kaynak klip adayının küçük resmi: denetimde karelerle karşılaştırılır
        f = klasor / f"{a['id']}_kucuk.jpg"
        try:
            import requests
            r = requests.get(f"https://i.ytimg.com/vi/{a['id']}/hqdefault.jpg", timeout=20)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                f.write_bytes(r.content)
                a["kucuk"] = str(f)
        except Exception:  # noqa: BLE001
            pass
    return out, kaynaklar


def dosya_etiketleri(cid):
    """mp4'ün kap etiketleri (ffprobe). Platformdan indirilen dosyada üretici uygulamanın izi çoğu zaman silinir; TikTok 'aigc_info' etiketini tutar."""
    import subprocess
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format_tags", "-of", "json", str(C.yol(cid) / "kaynak.mp4")],
                           capture_output=True, text=True, timeout=30)
        t = (json.loads(r.stdout or "{}").get("format") or {}).get("tags") or {}
    except Exception:  # noqa: BLE001
        return {}
    k = {a: v for a, v in t.items() if a.lower() not in ("major_brand", "minor_version", "compatible_brands", "vid_md5")}
    try:
        tip = json.loads(t.get("aigc_info") or "{}").get("aigc_label_type")
        if tip:
            k["yapay_zeka_etiketi_dosyada"] = tip
    except Exception:  # noqa: BLE001
        pass
    return k


def _uc_kareler(cid):
    """Videonun ilk anı ve son 2 saniyesinden kareler: araç filigranı, CapCut bitiş kartı, logo burada görünür."""
    import subprocess
    d = C.oku(cid)
    sure = float((d.get("kaynak") or {}).get("sure") or 0)
    if sure <= 0:
        return []
    klasor = C.yol(cid) / "is_ara"
    klasor.mkdir(exist_ok=True)
    out = []
    for ad, sn in (("uc_bas", 0.2), ("uc_son1", max(0, sure - 1.6)), ("uc_son2", max(0, sure - 0.25))):
        f = klasor / f"{ad}.jpg"
        try:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{sn:.2f}", "-i", str(C.yol(cid) / "kaynak.mp4"), "-frames:v", "1",
                            "-vf", "scale='min(720,iw)':-2", str(f)], capture_output=True, timeout=30)
        except Exception:  # noqa: BLE001
            continue
        if f.exists() and f.stat().st_size > 0:
            out.append(f)
    return out


VIDEO_ISLEV = ("function-generate-videos", "function-video-lip-sync", "function-video-inpainting", "function-generate-dubbing",
               "function-voice-cloning", "function-video-enhancer")


def guncel_modeller():
    """Güncel yapay zekâ video modelleri: sunra.ai'nin herkese açık model kataloğu (anahtar istemez, ücretsiz; 2026-10-29 kullanıcı buldu).
    Modelin bilgisi eskiyebilir; çözümleme bir yol önerirken bugünkü sürüm adlarını buradan alır. Kanıt DEĞİLDİR. Günde bir kez okunur,
    `content/.sunra_katalog.json`; okunamazsa önbellek ya da boş. Ayarlar'da kapatılırsa hiç okunmaz."""
    if not C.ayar().get("sunra"):
        return []
    import time
    import requests
    yol = C.KOK / ".sunra_katalog.json"
    try:
        o = json.loads(yol.read_text(encoding="utf-8"))
        if time.time() - o.get("t", 0) < 86400:
            return o.get("satirlar") or []
    except Exception:  # noqa: BLE001
        o = {}
    tum, son = [], None
    try:
        for _ in range(10):
            j = requests.get("https://api.sunra.ai/v1/models", params={"limit": 100, **({"starting_after": son} if son else {})},
                             headers=UA, timeout=20).json()
            tum += j.get("data") or []
            if not j.get("has_more") or not j.get("data"):
                break
            son = j["data"][-1]["id"]
    except Exception:  # noqa: BLE001
        return o.get("satirlar") or []
    satirlar = []
    for m in tum:
        if not set(m.get("functions") or []) & set(VIDEO_ISLEV):
            continue
        satirlar.append(f"{m.get('display_name') or m.get('alias')}: {(m.get('description') or '').strip()[:150]}")
    if satirlar:
        yol.write_text(json.dumps({"t": time.time(), "satirlar": satirlar}, ensure_ascii=False), encoding="utf-8")
    return satirlar or o.get("satirlar") or []


DIL_EN = "\n\nDİL (bu kural yukarıdaki dil kurallarının önüne geçer): kullanıcı İNGİLİZCE kullanıyor. JSON'daki kullanıcıya görünen bütün metinleri (baslik, ozet, araclar, adimlar, sik_hatalar, gerekenler, yapilacaklar, emin_olmadiklarim, kanit, hareket_tutanagi, sizin_icin, kaynak_klip, claude_yolu, sema) sade İNGİLİZCE yaz; uygulama menü adlarını İngilizce arayüzde göründüğü gibi ver (Türkçe karşılık ekleme). JSON anahtarları ve kod değerleri (yontem, guven, dayanak, zorluk, kim) değişmez."


def _kareler(cid, n=12):
    k = sorted((C.yol(cid) / "kareler").glob("*.jpg"))
    if len(k) <= n:
        return k
    return [k[round(i * (len(k) - 1) / (n - 1))] for i in range(n)]


def coz(cid):
    import claude_yaz
    d = C.oku(cid)
    t, k = d.get("tarif") or {}, d.get("kaynak") or {}
    if not t:
        raise RuntimeError("Önce video çözümlenmeli.")
    C.guncelle(cid, durum="planlaniyor", adim="Yapılış yöntemi çözülüyor")
    C.log(cid, "Yapılış yöntemi çözülüyor")
    sakla = bool(d.get("kanit_sakla"))
    aciklama = "" if sakla else (k.get("aciklama") or "")      # deneme: açıklama, başlık, platform sayfası, yorumlar ve dosya etiketi gizli (content_test)
    try:
        if sakla:
            raise StopIteration
        inf = json.loads(next(C.yol(cid).glob("kaynak*.info.json")).read_text(encoding="utf-8"))
        aciklama = (inf.get("description") or aciklama)[:1500]
        etiket = inf.get("tags") or []
        if etiket:
            aciklama += "\nEtiketler: " + ", ".join(etiket[:30])
        if inf.get("track") or inf.get("artist"):
            aciklama += f"\nMüzik: {inf.get('track') or ''} {inf.get('artist') or ''}"
    except Exception:  # noqa: BLE001
        pass
    link = d.get("link") or ""
    C.log(cid, "Platform sayfası, yorumlar ve dosya etiketleri okunuyor")
    sayfa = {} if sakla else sayfa_kaniti(link)
    yorum = [] if sakla or not C.ayar().get("yorumlar") else yorumlar(link, yazar_uid=sayfa.pop("_yazar_uid", None))
    sayfa.pop("_yazar_uid", None)
    dosya = {} if sakla else dosya_etiketleri(cid)
    uc = _uc_kareler(cid)
    C.log(cid, "Şarkı tanınıyor; kütüphanede aynı sesi taşıyan videolar aranıyor")
    kutup = kutuphane_eslesme(cid)
    mu = sayfa.get("muzik") or {}
    if mu and not mu.get("ozgun_ses") and mu.get("ad"):
        sarki = {"sarki": mu.get("ad"), "sanatci": mu.get("sahibi"), "kaynak": "platform"}
    elif sayfa.get("tiktok_sarki_eslesmesi"):
        sarki = {"sarki": sayfa["tiktok_sarki_eslesmesi"][0], "kaynak": "platform (TikTok şarkı eşleşmesi)"}
    else:
        sarki = K.sarki_tani(cid, konusma_var=len(_kelimeler(t.get("ses_yazisi"))) > 20)
        if not sarki:
            sarki = sarki_bul(t.get("ses_yazisi"))
            if sarki:
                sarki["kaynak"] = "sözlerden tahmin"
    C.log(cid, f"Şarkı: {sarki.get('sarki')} ({sarki.get('kaynak')}); akım web'de aranıyor" if sarki else "Şarkı bulunamadı; akım web'de aranıyor")
    if sakla:
        t = dict(t, ozet="")                    # ilk inceleme özeti açıklamayı görmüş olabilir
    bilinen = " / ".join(x for x in [k.get("baslik"), (sayfa.get("aciklama") or aciklama)[:300], (t.get("ozet") or "")[:300],
                                     "yapay zekâ etiketi var" if (sayfa.get("yapay_zeka_etiketi") or sayfa.get("yapay_zeka_etiket_turu")) else ""] if x)
    try:
        web = K.web_trend(sarki, sayfa.get("tiktok_onerilen_aramalar") or [], bilinen=bilinen, dil=d.get("dil") or "tr")
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] web araması yapılamadı: {e}", flush=True)
        web = {}
    if web:
        C.log(cid, f"Web'de akım bulundu: {(web.get('akim') or '')[:80]}")
    replik = {}
    if len(_kelimeler(t.get("ses_yazisi"))) >= 15:
        C.log(cid, "Konuşmanın hangi film ya da diziden geldiği aranıyor")
        try:
            replik = K.replik_ara(t.get("ses_yazisi"), bilinen=bilinen, dil=d.get("dil") or "tr")
        except Exception as e:  # noqa: BLE001
            print(f"[content {cid}] replik araması yapılamadı: {e}", flush=True)
        if replik:
            C.log(cid, f"Konuşmanın kaynağı bulundu: {replik.get('eser')} {replik.get('yil') or ''}".strip())
    C.log(cid, "Aynı sesle ya da aynı kalıpla yapılmış başka videolar aranıp karşılaştırılıyor")
    benzerler, ozgun = [], {}
    try:
        ozgun = {} if sakla else B.ozgun_ses(cid, sayfa)
        benzerler = B.karsilastir(cid, sarki, web, {} if sakla else sayfa)
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] benzer video karşılaştırması yapılamadı: {e}", flush=True)
    if benzerler:
        C.log(cid, f"{len(benzerler)} benzer video karşılaştırıldı; en yakını: {benzerler[0]['yorum']}")
    C.guncelle(cid, sayfa_kaniti=sayfa, yorumlar=yorum, dosya_etiketleri=dosya, kutuphane_eslesme=kutup, sarki=sarki, web_trend=web, replik=replik,
               benzerler=[{a: b.get(a) for a in ("link", "baslik", "kanal", "sure", "ses", "gorsel", "gorsel_en", "yorum")} for b in benzerler], ozgun_ses=ozgun)
    seritler = [b["serit"] for b in benzerler if b.get("serit")][:2]
    istem = ISTEM.format(
        sayfa=json.dumps(sayfa, ensure_ascii=False)[:2400] if sayfa else "(yok)",
        dosya=json.dumps(dosya, ensure_ascii=False)[:400] if dosya else "(yok)",
        yorumlar=json.dumps(yorum, ensure_ascii=False)[:3000] if yorum else "(yok)", uc=len(uc), serit=len(seritler),
        sarki=json.dumps(sarki, ensure_ascii=False) if sarki else "(bulunamadı)",
        web=json.dumps(web, ensure_ascii=False)[:2500] if web else "(bulunamadı)",
        replik=json.dumps(replik, ensure_ascii=False)[:1500] if replik else ("(konuşma kısa, aranmadı)" if len(_kelimeler(t.get("ses_yazisi"))) < 15 else "(web'de bulunamadı)"),
        modeller="\n".join(guncel_modeller()[:70])[:6000] or "(okunamadı)",
        kutuphane=json.dumps(kutup, ensure_ascii=False)[:2500] if kutup else "(yok)",
        benzer=B.istem_metni(benzerler, ozgun)[:3000],
        statik=(f"FOTOĞRAF GÖNDERİSİ: {k['statik']} görsel (video değil; kareler görsellerin kendisi, her görsel {k.get('statik_sn', 3)} sn'lik slayt, ses yok). Hareket arama; yöntem fotoğraf düzenleme, yapay zekâ görseli, kolaj ya da filtre olabilir; adımlar fotoğraf uygulamasına göre."
                if k.get("statik") else "video"),
        baslik=k.get("baslik") or "-", kanal=k.get("kanal") or "-", aciklama=aciklama or "-",
        sure=float(k.get("sure") or 0), w=k.get("w") or 0, h=k.get("h") or 0,
        sahneler=", ".join(f"{s['no']}: {s['bas']:.1f}-{s['bit']:.1f} sn {s.get('aciklama') or ''}" for s in t.get("sahneler") or [])[:2500],
        ses=(t.get("ses_yazisi") or "(konuşma yok)")[:1500],
        yazilar="; ".join(f"{y['sn']:.1f} sn: {y['metin']}" for y in t.get("yazilar") or [])[:1200] or "(yok)",
        ozet=(t.get("ozet") or "")[:600], istek=(d.get("istek") or "").strip() or "(yok)",
        olcum="\n".join(A.olc(d)) or "(ölçülemedi)", defter=A.defter_metni(),
        duzeltme=(d.get("kullanici_duzeltmesi") or "").strip() or "(yok)", dersler=D.dersler_blogu(haric=d.get("test_kaynak")))
    if d.get("dil") == "en":
        istem += DIL_EN
    try:
        izg = K.izgaralar(cid)
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] ızgara çıkarılamadı: {e}", flush=True)
        izg = []
    goruntu = (izg or _kareler(cid, 16)) + [Path(x) for x in seritler]
    y = claude_yaz.json_coz(claude_yaz.sor_gorsel(istem, [str(x) for x in goruntu + uc], model_adi="opus"))
    if not y or not y.get("adimlar"):
        raise RuntimeError("Yapılış yöntemi çıkarılamadı (yanıt okunamadı).")
    C.log(cid, "Bu videoyu anlatan öğretici videolar aranıyor")
    sorgular = [q for q in (y.get("ogretici_aramalari") or []) if isinstance(q, str)][:3]
    if (sayfa.get("baglantilar") or [{}])[0].get("sablon", {}).get("ad"):
        sorgular.insert(0, f"{sayfa['baglantilar'][0]['sablon']['ad']} capcut template tutorial")
    kk = y.get("kaynak_klip") or {}
    if web.get("arama"):
        sorgular.append(web["arama"])
    if kk.get("olasi"):
        sorgular += [q for q in (kk.get("arama") or []) if isinstance(q, str)][:2]
    eylem = (kk.get("eylem") or "").strip()
    if sarki.get("sarki"):
        sorgular.append(f"{sarki['sarki']} {eylem} ai trend".replace("  ", " "))
        if eylem:
            sorgular.append(f"{sarki['sarki']} {eylem}")
    elif eylem:
        sorgular.append(f"{eylem} ai trend tutorial")
    bilinen_kutup = "\n".join(f"Kütüphanedeki aynı sesli video: {x['ne']} / {x['yontem']} / {x['aciklama']}" for x in kutup)
    try:
        ogr, kaynak_aday = ogreticiler(cid, sorgular, (y.get("ozet") or "") + "\n" + (k.get("baslik") or "") + "\n" + aciklama[:600]
                                       + (f"\nŞarkı: {sarki.get('sarki')} {sarki.get('sanatci') or ''}" if sarki else "")
                                       + (f"\nOlası kaynak an: {kk.get('ne')}" if kk.get("ne") else "")
                                       + (f"\nWeb'e göre akım: {web.get('akim')}; canlandırdığı an: {web.get('orijinal_an')}" if web else "")
                                       + ("\n" + bilinen_kutup if bilinen_kutup else ""))
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] öğretici aranamadı: {e}", flush=True)
        ogr, kaynak_aday = [], []
    C.guncelle(cid, ogreticiler=[{a: o.get(a) for a in ("baslik", "kanal", "link", "sure")} for o in ogr],
               kaynak_aday=[{a: o.get(a) for a in ("baslik", "kanal", "link", "sure")} for o in kaynak_aday])
    C.log(cid, f"{len(ogr)} öğretici video bulundu; adımlar doğruluk için denetleniyor" if ogr else "Öğretici video bulunamadı; adımlar doğruluk için denetleniyor")
    ogr_metin = "\n\n".join(f"[{o['baslik']}] {o['link']} ({o['kanal']}, {o['sure']} sn)\nAçıklama: {o['aciklama'][:900]}\nKonuşma: {o['metin'][:3500]}"
                              for o in ogr) or "(bulunamadı)"
    kanit = istem[istem.find("SAYFA KANITI"):istem.find("Ekte videodan")][:9000]
    if d.get("kullanici_duzeltmesi"):
        kanit += f"\nKULLANICININ DÜZELTMESİ (bu videonun gerçeği; kesin kabul et): {d['kullanici_duzeltmesi']}"
    kanit += f"\nGEÇMİŞ HATALARDAN DERSLER: {D.dersler_blogu(haric=d.get('test_kaynak'))}"
    kucukler = [a for a in kaynak_aday if a.get("kucuk")]
    kaynak_metin = "\n".join(f"{i + 1}. [{a['baslik']}] {a['link']} ({a['kanal']}, {a['sure']} sn)" for i, a in enumerate(kaynak_aday)) or "(yok)"
    if kucukler:
        kaynak_metin += (f"\nEkteki resimlerin SON {len(kucukler)} tanesi bu adayların küçük resimleri (sırayla: "
                         + ", ".join(a["baslik"][:60] for a in kucukler) + "). Videonun karelerindeki hareket/kompozisyonla karşılaştır.")
    try:
        y2 = claude_yaz.json_coz(claude_yaz.sor_gorsel(DENETIM.format(kanit=kanit, ogretici=ogr_metin, kaynak=kaynak_metin, benzer=B.istem_metni(benzerler, ozgun)[:2000],
                                                                      taslak=json.dumps(y, ensure_ascii=False)) + (DIL_EN if d.get("dil") == "en" else ""),
                                                       [str(x) for x in (izg[:6] or _kareler(cid, 8)) + uc] + seritler[:1] + [a["kucuk"] for a in kucukler], model_adi="opus"))
        if y2 and y2.get("adimlar"):
            y = y2
    except Exception as e:  # noqa: BLE001
        print(f"[content {cid}] denetim yapılamadı: {e}", flush=True)
    import time
    y = K.kademe(y, sayfa, dosya, ogr, web)
    if web.get("kaynaklar"):
        y["web_kaynaklar"] = web["kaynaklar"]
    if replik.get("kaynaklar"):
        y["web_kaynaklar"] = (y.get("web_kaynaklar") or []) + [dict(k, ne=f"Konuşmanın kaynağı ({replik.get('eser')}): {k.get('ne') or ''}".strip(": "))
                                                                  for k in replik["kaynaklar"]]
    y["zaman"] = time.time()
    C.guncelle(cid, yontem=y, durum="yontem", adim="Rehber hazır")
    C.log(cid, "Rehber hazır")
    return y
