# xbox-samsung-subtitles-tv

**Xbox oyunlarına Samsung TV'de canlı Türkçe altyazı.** Oyun TV'de doğrudan HDMI'dan, gecikmesiz oynanır; İngilizce altyazılar PC'de okunup çevrilir ve TV'deki küçük bir uygulama Türkçeyi oyunun üstüne yazar.

> 🇬🇧 English summary at the [bottom](#english).

- Oyuna, oyun dosyalarına ya da konsola **dokunmaz**; yalnızca ekrandaki yazıyı okur.
- Ekran yansıtma, PC'yi TV'ye HDMI ile bağlama ya da capture kart **gerekmez**.
- **GTA V (Xbox Series X)** ile test edildi. Asıl hedef **GTA VI**; altyazı bölgesi ve çeviri komutu oyuna göre ayarlanabilir.

## Nasıl çalışır?

```
Xbox Series X/S ──HDMI──► Samsung TV (Tizen)
      │                     └─ Altyazı TV uygulaması
      │                          • HDMI görüntüsü tam ekran, uygulamanın ARKASINDA (tvwindow)
      │                          • Türkçe altyazıyı İngilizcenin hemen üstüne yazar
      │                                    ▲  WebSocket (yerel ağ)
      └─ Xbox uygulaması "Uzaktan oynat" ──► Windows PC
                                            └─ LunaTranslator
                                               • Windows 11 OCR ile altyazı şeridini okur (~70 ms)
                                               • altyazı filtresi: plaka, tabela, HUD yazılarını atar
                                               • çeviri: Gemini + Google yarışır (≤1 sn)
                                               • ws://PC_IP:2333/api/ws/text/trans
```

Altyazı oyundaki İngilizceden yaklaşık **1–2 saniye** sonra TV'ye gelir.

## Gerekenler

| | |
|---|---|
| Konsol | Xbox Series X/S (ya da One), **uzaktan özellikler açık** |
| TV | Samsung Smart TV, Tizen (2016 ve sonrası; QN90A / Tizen 6.0 ile test edildi) |
| PC | Windows 11 (OCR için), konsol ve TV ile **aynı yerel ağda** |
| Yazılım | [Xbox uygulaması](https://www.xbox.com/apps/xbox-app-for-pc), [LunaTranslator](https://github.com/HIllya51/LunaTranslator/releases), [Tizen SDK (CLI)](https://developer.tizen.org/development/tizen-studio/download) |
| Hesap | Samsung hesabı (TV sertifikası için, ücretsiz) |
| İsteğe bağlı | [Gemini API anahtarı](https://aistudio.google.com/apikey) (daha doğal çeviri; yoksa yalnızca Google kullanılır) |

## Hızlı kurulum (önerilen)

1. Repoyu indir: yeşil **Code → Download ZIP**, bir klasöre çıkar (ya da `git clone`).
2. **`KUR.bat`**'a çift tıkla. Betik sırayla:
   Tizen SDK'yı indirip kurar → Samsung sertifika eklentilerini kurar ve onarır → LunaTranslator'ı indirir (ya da mevcut klasörünü sorar), eklentileri kopyalar ve **tüm ayarlarını yapar** → güvenlik duvarı izni → TV'ye bağlanır → Sertifika Yöneticisi'ni açar → uygulamayı derleyip TV'ye yükler.
3. Senin yapacakların, betik sırası gelince söyler:
   - TV'de geliştirici modunu açmak (aşağıda 1. adım)
   - Windows onay pencerelerine "Evet" demek
   - Sertifika Yöneticisi'nde Samsung hesabınla giriş yapmak (aşağıda 3. adım)
   - İsteğe bağlı: kendi Gemini API anahtarını girmek (boş bırakılırsa yalnızca ücretsiz Google Çeviri)

Betik yarıda kalırsa tekrar çalıştır; tamamlanmış adımları atlar. Tek bir adımı yeniden yapmak için:
`KUR.bat -Adimlar luna` (adımlar: `onkosul, tizen, eklenti, luna, guvenlik, tv, sertifika, yukle`).

### 🤖 Yapay zekâ asistanıyla kurulum
[Claude Code](https://claude.com/claude-code) gibi bilgisayarında komut çalıştırabilen bir yapay zekâ asistanın varsa, şunu yapıştır:

```text
https://github.com/benorhanuysal/xbox-samsung-subtitles-tv reposunu klonla ve README'ye göre
bu bilgisayara kur. Önce KUR.bat'ı (scripts\kurulum.ps1) kullan; bir adım hata verirse
README'deki "Sorun giderme" tablosuna bak, sebebini bul ve düzelt. Windows'um Türkçeyse Java
tabanlı Tizen araçlarını -Duser.language=en ile çalıştır. TV'de yapılacakları, Samsung hesabı
girişini ve onay pencerelerini bana adım adım söyle; şifre ya da API anahtarı isteme, onları
ben gireceğim. Bitince Xbox uzaktan oynatma + LunaTranslator + TV uygulamasıyla uçtan uca test et.
```

## Elle kurulum

### 1. TV'yi geliştirici moduna al
1. TV'de **Uygulamalar** ekranını aç, kumandayla `1 2 3 4 5` tuşla.
2. **Developer Mode: On**, **Host PC IP**: PC'nin IP adresi (`scripts\2_tv_bagla_ve_sertifika.bat` bunu ekrana yazar).
3. TV'yi tamamen kapatıp aç.
4. TV'nin IP adresini not et: *Ayarlar → Genel → Ağ → Ağ Durumu*.

### 2. Tizen SDK ve Samsung eklentileri
1. Tizen SDK **CLI** kurulum dosyasını `C:\tizen-studio` klasörüne kur.
2. Paket yöneticisinde (`C:\tizen-studio\package-manager\package-manager.exe`, yönetici olarak) şunları kur:
   **Samsung Certificate Extension** (`cert-add-on`) ve **Certificate Manager**.
3. Paket yöneticisi "kurulamadı" dese bile dosyalar genelde inmiştir: `scripts\sertifika_eklentisini_kaydet.bat` çalıştır.

### 3. Samsung sertifikası
`scripts\2_tv_bagla_ve_sertifika.bat` → TV IP'sini gir → açılan Sertifika Yöneticisi'nde:
**+ → Samsung → TV → profil adı `AltyaziTV`** → yeni author sertifikası (şifre belirle) → tarayıcıda Samsung hesabıyla giriş → distributor: **Public**, DUID listesinde TV otomatik görünür → Finish.

### 4. TV uygulamasını yükle
`scripts\3_paketle_ve_tvye_yukle.bat` → derler, imzalar, TV'ye yükler ve başlatır. TV'de **Altyazı TV** açılır.

### 5. LunaTranslator
1. `luna\kur.bat` → LunaTranslator klasörünü gir (Luna kapalıyken). Filtre ve çeviriciyi kopyalar.
2. LunaTranslator'ı aç ve ayarla (menü adları İngilizce / Türkçe arayüz):

| Ayar | Değer |
|---|---|
| Metin girdi / Text Input | **OCR** |
| OCR motoru | **SnippingTool** (Windows 11 OCR — hızlı ve doğru) |
| OCR menzilini seç / Select OCR Region | Oyundaki **altyazı şeridi** (ekranın alt ortası; mini harita ve sağ alt HUD hariç) |
| Otomatik çalışma metodu / Automated Execution Method | **Periyodik çalışma**, İşletim döngüsü **0,3 sn** |
| Metin işleme → **Özel Python işleme** / Custom Python Processing | **Açık** (`mypost.py`) |
| Çeviri: **Özel çevirim** / Custom Translation | **Açık**; diğer tüm çeviriciler **kapalı** (yoksa TV'ye her cümle iki kez gider) |
| Ağ servisleri / Network Service | **Açık**, port **2333** |

3. `scripts\1_guvenlik_duvari_izni.bat` → **Evet** (TV'nin PC'ye bağlanabilmesi için).

### 6. (İsteğe bağlı) Gemini
**Büyük modeller için genel arayüz / General LLM Interface** ayarlarına gir — ama bu çeviriciyi **açma**, sadece ayarlarını doldur (`selfbuild.py` oradan okur):
- API adresi: `https://generativelanguage.googleapis.com`
- API Key: anahtarın · Model: `gemini-flash-lite-latest`
- Özel promt (örnek GTA için):
  > You translate English video game subtitles from Grand Theft Auto into natural, casual Turkish. Output only the Turkish translation, nothing else. Keep it short like a subtitle. Never translate character names, place names, vehicle, weapon or brand names. Keep street slang and swearing in a natural Turkish equivalent. If the input is not a sentence (HUD text, a name, a number), output it unchanged.

Anahtarı **faturalandırması kapalı** bir projede oluştur ki ücretsiz katmanda kal. Sınıra takılınca (429) çevirici 30 sn Gemini'yi denemez; o arada pakette ya da önbellekte olmayan satırlar atlanır (Google'ın uzun, harfiyen çevirisi oyunda okunamadığı için kapalı: `GOOGLE_YEDEK = False`).

### 7. (Önerilen) Altyazı motoru — ekranı biz okuruz
`motor/motor.py`, Luna'nın ekran okuma döngüsünün yerine geçer. Çeviri, filtre ve TV/OBS yayını Luna'da kalır; TV uygulaması değişmez.
```
ekran şeridi ─► gölgeli ön işleme ─► Luna /api/ocr ─► dengeleyici ─► Luna /api/textinput ─► (filtre, paket, önbellek, Gemini) ─► TV, OBS
```
- **Gölgeli ön işleme** (`motor/onisleme.py`): Altyazı beyaz yazı ve sağ-aşağıda koyu gölgeden oluşur. Yalnız gölgesi olan açık pikselleri bırakıp "beyaz zemin üstünde siyah yazı" yapar. Plaka, harita, gökyüzü gibi gölgesiz parlak alanlar kendiliğinden elenir.
- **Dengeleyici** (`motor/dengeleyici.py`): Satırı iki benzer okumadan sonra ya da cümle işaretiyle bitince bir kez gönderir. Ekranda duran satırın kötü yeniden okumasını yok sayar. Satır uzarsa "değiştir" gönderir. 0,8 sn boş okumada satır gitti sayılır; 1,5 sn içinde geri gelirse beklemeden gönderilir.
- **Ölçüm** (kayıttan 80 sn'lik telefon konuşması, saniyede 4 kare, doğruluk = satırın GTA V paketinde birebir bulunması):

  | | Doğru okunan kare | Çöp/bozuk farklı okuma | Gönderilen satır |
  |---|---|---|---|
  | Luna'nın okuması (ham) | %75 | 20 | 15 (3'ü plaka) |
  | **Motor (gölgeli + dengeleyici)** | **%99** | **2** | **12 / 12 doğru** |

  Aynı bölümde 12 satırın 12'si paketten 0 ms'de çevrildi; Luna'nın kendi okumasıyla bu oran gerçek oyun günlüğünde %17'ydi.
- Yalnız Xbox uzaktan oynatma sesi akarken okur. Oyun yokken masaüstündeki koyu zemin + beyaz yazılar (kod editörü vb.) TV'ye gitmez.
- Kurulum: `pip install numpy pillow mss pycaw`. Luna kapalıyken `python motor\motor.py --luna-ocr kapat` (Luna'nın kendi okuması kapanır, yoksa TV'ye iki akış gider). Eski düzene dönmek için `--luna-ocr ac`. Okuma bölgesi `motor\motor_ayar.json`'da (`"bolge": [x, y, genişlik, yükseklik]`, 4K fiziksel piksel), günlük `motor\motor.log`.
- Kayıttan deneme (oyun açmadan): `python motor\motor.py --video kayit.mkv --bas 160 --sure 60 --olcek 1 --kuru`.
- GTA 6 için: Yöntem altyazının gölgeli beyaz yazı olmasına dayanır (Rockstar stili). Farklı çıkarsa `motor_ayar.json`'da `"on_isleme": "ham"` ile eski okumaya dönülür.

### 8. (Önerilen) Oyun çeviri paketi + kalıcı önbellek
Çevirici her satır için şu sırayla bakar: **önbellek → oyun paketi → Gemini**.
- **Oyun paketi:** hazır insan çevirisi; pakette olan satır **0 ms**'de gelir, Gemini kotası harcanmaz. GTA V paketi (~190 bin satır; hikâye GTA TR / TechnoGame yamasından, gerisi Claude ile çevrilip gözden geçirilmiş) [CouchSubs](https://github.com/yorulmazsinan/couchsubs) projesinin; bu repoya konmaz (AGPL-3.0, çeviri hakları sahiplerinde), kişisel kullanım için indirilir:
  ```powershell
  New-Item -ItemType Directory -Force "$env:USERPROFILE\LunaTranslator\userconfig\paketler"
  Invoke-WebRequest https://raw.githubusercontent.com/yorulmazsinan/couchsubs/main/core/Sources/CouchSubsCore/Resources/packs/gta-v.json.gz -OutFile "$env:USERPROFILE\LunaTranslator\userconfig\paketler\gta-v.json.gz"
  ```
  Eşleşme: satır küçük harfe çevrilip noktalama atılır (`Take out the enemies,` = `Take out the enemies.`); bulunmazsa konuşmacı etiketi (`LESTER: ...`) ayrılıp, sonra cümle cümle denenir. Gerçek oyun günlüğümüzde farklı satırların ~%17'si birebir eşleşti (çoğu görev cümlesi); kalanlar OCR'ın yarım/hatalı okuduğu satırlar.
- **Kalıcı önbellek** (`userconfig\ceviri_onbellek.jsonl`): Gemini'nin her çevirisi saklanır; tekrar eden satır Luna kapanıp açılsa da anında ve hep aynı çeviriyle gelir. Dosyayı silmek önbelleği sıfırlar.
- **OCR düzeltmeleri** (`mypost.py`): `l'm` → `I'm`, satırın başına yapışan görev mesafesi (`23m CESARE: ...`) atılır; ikisi de paketin eşleşmesini artırır.

## Kullanım
1. Xbox uygulaması → konsol → **Uzaktan oynat** → pencereyi **tam ekran ve en önde** tut (Luna ekranın o bölgesini okur).
2. LunaTranslator'ı aç.
3. TV'de **Altyazı TV**'yi aç → ilk açılışta **KIRMIZI** → PC IP'sini gir (nokta için OK) → KIRMIZI ile kaydet.
4. Oyun kumandasını (controller) **PC'ye** bağlayıp oyna; uzaktan oynatma kontrolü PC'ye alır. Görüntüyü TV'den, HDMI'dan gecikmesiz izle.

| Kumanda | İşlev |
|---|---|
| KIRMIZI | Ayarlar (PC IP / port) |
| YEŞİL | Altyazıyı aç / kapat |
| SARI | Yazı boyutu |
| MAVİ | Sonraki HDMI girişi |
| YUKARI / AŞAĞI | Altyazı konumu |
| OK | Yardım · GERİ: çıkış |

## Sorun giderme

| Belirti | Sebep / çözüm |
|---|---|
| Sertifika Yöneticisi'nde Samsung'a basınca pencere kapanıyor; "There is no ...\tools\sdb" | **Türkçe Windows + Java "I" hatası.** Yöneticiyi `scripts\2_tv_bagla_ve_sertifika.bat` ile aç (İngilizce yerel ayar zorlar). |
| `tizen package` → `NullPointerException` (profiles.xml) | Aynı Türkçe "I" hatası: `set JAVA_TOOL_OPTIONS=-Duser.language=en -Duser.country=US` (betikler bunu yapar). |
| Kurulum sessizce başarısız ("Failed to install") | `config.xml`'de paket kimliği **tam 10 karakter** olmalı. |
| `package-manager-cli.exe` yönetici istiyor; JDK bozuldu | Paket yöneticisini JDK'nın bir **kopyasıyla** çalıştır; kendi JDK'sını güncellerken yarıda bırakabiliyor. |
| TV bağlanmıyor | Güvenlik duvarı betiği, aynı ağ, Luna'da Ağ servisleri açık mı? Luna açıldıktan sonra servis birkaç saniyede başlar; TV uygulamasını yeniden aç. |
| Plaka, tabela, harita yazıları çevriliyor | OCR bölgesi altyazı şeridinden geniş; daralt. `mypost.py` kısa/HUD satırlarını eler. |
| Hiç altyazı gelmiyor | Uzaktan oynatma penceresi önde ve tam ekran mı? Önünde başka pencere varsa Luna onu okur. |
| Çeviri hangi motordan geldi? | `LunaTranslator\userconfig\altyazi_ceviri.log` |

## Başka oyun / başka dil
- **Hazır oyun ayarları:** [`oyunlar/`](oyunlar/) klasörü (şu an: [GTA V](oyunlar/gta-v.md)). Senin oyunun yoksa ekle; aşağıya bak.
- **Okuma bölgesi:** Luna'da oyunun altyazı şeridine göre seç.
- **TV'de konum:** YUKARI/AŞAĞI ile Türkçeyi oyunun altyazısının hemen üstüne getir.
- **Dil:** `luna/selfbuild.py` başındaki `KAYNAK_DIL`, `HEDEF_DIL`, `HEDEF_DIL_ADI`; Latin alfabesi olmayan diller için `_latin_mi` kontrolünü kaldır.
- **Filtre:** `luna/mypost.py` (en az kelime/harf, HUD kalıpları).

## Klasörler
```
KUR.bat   tek tık kurulum (scripts/kurulum.ps1)
tv-app/   Samsung TV (Tizen) web uygulaması: tvwindow + WebSocket + altyazı
luna/     LunaTranslator eklentileri: mypost.py (filtre), selfbuild.py (Gemini+Google), kur.bat
scripts/  kurulum.ps1, güvenlik duvarı, TV bağlantısı + sertifika, paketle-yükle, eklenti onarımı
```

Gemini anahtarı repoda **yok**: `selfbuild.py` herkesin kendi bilgisayarındaki LunaTranslator ayarlarından okur. Katkı gönderirken IP adresi, sertifika dosyası ya da API anahtarı eklemeyin.

## Katkıda bulun
En değerli katkı **yeni bir oyunun ayarı**: okuma bölgesi, TV'deki altyazı konumu, çeviri komutu. GTA VI çıktığında ilk ayarı paylaşan sen ol 🙂

- 🎮 **Oyun ayarı:** [`oyunlar/SABLON.md`](oyunlar/SABLON.md) ile PR gönder ya da git bilmiyorsan **Issues → "Oyun ayarı paylaş"** formunu doldur.
- 🐞 **Hata:** **Issues → "Hata bildir"**.
- 💻 **Kod:** fork → değişiklik → TV'de/Luna'da dene → Pull Request.

Ayrıntılar ve kod kuralları: [CONTRIBUTING.md](CONTRIBUTING.md). **Hiçbir yere API anahtarı, IP adresi, sertifika dosyası ya da TV DUID'i koyma.**

## Uyarı
Resmî bir proje değildir; Microsoft/Xbox, Samsung, Rockstar Games ya da LunaTranslator ile bağlantısı yoktur. Oyuna müdahale etmez, yalnızca PC'deki uzaktan oynatma görüntüsünü okur; yine de çevrim içi oyunlarda kullanım sorumluluğu sana aittir. Gemini kullanıyorsan Google'ın kullanım koşulları ve kotaları geçerlidir.

## Lisans
[MIT](LICENSE). Gömülü Noto Sans yazı tipi: SIL Open Font License 1.1 ([tv-app/fonts/OFL.txt](tv-app/fonts/OFL.txt)).
Teşekkürler: [LunaTranslator](https://github.com/HIllya51/LunaTranslator) (OCR, ağ servisi, eklenti altyapısı).

---

## English

**Live translated subtitles for Xbox games on a Samsung (Tizen) TV.** You play directly on the TV over HDMI with zero added latency. The PC reads the game's English subtitles through Xbox Remote Play using LunaTranslator (Windows 11 OCR), translates them (Gemini and Google Translate race; the first good result within 1 s wins), and streams the text over a local WebSocket to a small Tizen web app. The app shows the HDMI input full-screen *behind* itself (`tizen.tvwindow`, `BEHIND`) and draws the translation just above the game's own subtitle. Tested with GTA V on Xbox Series X and a 2021 Samsung QN90A; built with GTA VI in mind. Translation target is Turkish by default; change `KAYNAK_DIL` / `HEDEF_DIL` / `HEDEF_DIL_ADI` in `luna/selfbuild.py` for other languages.

**Quick setup:** download the repo and run **`KUR.bat`** — it installs the Tizen SDK and Samsung certificate extension, downloads and fully configures LunaTranslator, adds the firewall rule, connects to the TV, opens Certificate Manager and deploys the app. You only enable Developer Mode on the TV, approve Windows prompts and sign in to your Samsung account. Re-running is safe (finished steps are skipped). With an AI coding assistant, paste the prompt from the Turkish section above.

Manual setup in short: enable TV Developer Mode → install Tizen SDK CLI + Samsung Certificate Extension → create a **Samsung** certificate profile named `AltyaziTV` (on non-English Windows, launch Certificate Manager with `-Duser.language=en`; `scripts\2_tv_bagla_ve_sertifika.bat` does this) → `scripts\3_paketle_ve_tvye_yukle.bat` → copy `luna/*.py` into LunaTranslator's `userconfig` and configure LunaTranslator as in the table above (OCR: SnippingTool, 0.3 s period, Custom Python Processing on, Custom Translation as the only translator, Network Service on port 2333) → allow TCP 2333 in Windows Firewall → open the app on the TV and enter the PC's IP with the RED button.

Not affiliated with Microsoft, Samsung, Rockstar Games or LunaTranslator. MIT licensed.
