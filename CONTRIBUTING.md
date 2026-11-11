# Katkıda bulunma

Teşekkürler! Bu proje, oyunlara kendi dilinde altyazı isteyen oyuncular için. Her katkı işe yarar: yeni bir oyunun ayarı, bir hata bildirimi, bir çeviri komutu iyileştirmesi ya da kod.

> 🇬🇧 English: contributions are welcome in English too. Game presets go to `oyunlar/`, bugs to Issues, code via Pull Request. **Never include IP addresses, certificates, passwords or API keys.**

## ⚠️ Önce: kişisel bilgi
Issue'ya, PR'a, ekran görüntüsüne ya da günlük dosyasına **asla** şunları koyma:

- **API anahtarları** (Gemini, Google vb.)
- **Samsung sertifika dosyaları ve şifresi** (`.p12`, `.pwd`, `.pri`, `.crt`, `device-profile.xml`)
- **TV'nin DUID'i**, ev ağının **IP adresleri**, Wi-Fi adı
- Windows kullanıcı adın ve klasör yolların (gerekiyorsa `C:\Users\<ad>\...` diye yaz)

Ekran görüntüsünde TV'nin ayar menüsü ya da bildirimler görünüyorsa önce kırp. `altyazi_ceviri.log` paylaşacaksan içinde yalnızca oyun metinleri olduğundan emin ol.

## 🎮 Oyun ayarı paylaşmak (en değerli katkı)
Yeni bir oyunda çalıştırdıysan, başkaları uğraşmasın:

1. [`oyunlar/SABLON.md`](oyunlar/SABLON.md) dosyasını kopyala → `oyunlar/oyun-adi.md` (küçük harf, tire ile: `red-dead-redemption-2.md`).
2. Doldur: **okuma bölgesi oran olarak** (her ekran çözünürlüğünde çalışsın), TV'deki altyazı konumu, varsa Gemini komutu, notlar. Örnek: [`oyunlar/gta-v.md`](oyunlar/gta-v.md).
3. PR gönder. Git bilmiyorsan **Issues → "Oyun ayarı paylaş"** formunu doldur, biz ekleriz.

Oranı hesaplamak: LunaTranslator'da seçtiğin bölgenin piksel değerlerini ekran genişliğine/yüksekliğine böl (ör. `260 / 1920 = 0.135`).

## 🐞 Hata bildirmek
**Issues → "Hata bildir"** formunu kullan. Şunlar çok yardımcı olur:

- Windows sürümü ve dili (**Türkçe Windows** birçok Java/Tizen hatasının sebebi), TV modeli, konsol
- Hangi adımda takıldın (`KUR.bat` çıktısı; kişisel bilgileri sil)
- Önce README'deki **Sorun giderme** tablosuna bak; çözüm orada olabilir

## 💻 Kod göndermek (Pull Request)
1. Repoyu **fork**'la, bir dal aç (`ozellik/kisa-ad` ya da `duzeltme/kisa-ad`).
2. Değişikliğini yap ve **gerçekten dene**:
   - `tv-app/` → `scripts\3_paketle_ve_tvye_yukle.bat` ile TV'de; `node --check tv-app/app.js`
   - `luna/` → dosyayı LunaTranslator'ın `userconfig` klasörüne kopyala (Luna kendini yeniden yükler) ve oyunda dene
   - `scripts/kurulum.ps1` → mümkünse temiz bir bilgisayarda; en azından ilgili adımı `KUR.bat -Adimlar <adim>` ile
3. PR açıklamasına neyi neden değiştirdiğini ve nasıl test ettiğini yaz.

### Kod kuralları
- Mevcut stile uy: değişken ve fonksiyon adları Türkçe, yorumlar kısa ve "neden"i anlatır.
- `.bat` dosyaları Windows satır sonuyla (CRLF) kalır; `.gitattributes` bunu sağlar.
- `scripts/kurulum.ps1` **UTF-8 BOM** ile kaydedilmeli (Windows PowerShell 5.1 Türkçe/Çince karakterleri ancak böyle okur) ve her adım **tekrar çalıştırılabilir** olmalı: yapılmışsa atla.
- LunaTranslator ayar dosyalarını yazarken **BOM'suz UTF-8** kullan (Luna BOM'lu dosyayı okuyamaz) ve yalnızca gereken anahtarlara dokun.
- Java/Tizen araçlarını çağırırken `-Duser.language=en -Duser.country=US` ekle.
- Yeni bir bağımlılık ya da indirme ekliyorsan yalnızca resmî kaynaklardan (Tizen, GitHub releases) olsun.

## Lisans
Katkıların [MIT lisansı](LICENSE) altında yayımlanır.
