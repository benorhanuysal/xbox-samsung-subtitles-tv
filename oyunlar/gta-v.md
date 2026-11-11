# GTA V (Xbox Series X)

| | |
|---|---|
| Test edildi | 11.2026 · Xbox Series X · Samsung QN90A (Tizen 6.0) · Windows 11 · 1920×1080 ekran |
| Oyun ayarı | Altyazılar: **Açık** (Ayarlar → Ekran → Altyazılar) |
| Durum | ✅ Çalışıyor |

## LunaTranslator okuma bölgesi
Uzaktan oynatma **tam ekranda**, ekran oranına göre (sol, üst, genişlik, yükseklik):

| | sol | üst | genişlik | yükseklik |
|---|---|---|---|---|
| Oran | 0.135 | 0.813 | 0.729 | 0.156 |
| 1920×1080 | 260 | 878 | 1400 | 168 |

GTA Online diyalogları uzun; daha dar bölge satırın başını/sonunu keser. Mini harita (sol alt) bölgenin dışında kalmalı. Araç plakaları bölgeye girebilir; `mypost.py` onları eler.

## TV'de altyazı konumu
`bottom: 150px`, yazı **40px** (uygulamanın varsayılanı). Türkçe, GTA'nın İngilizce altyazısının (1080p'de y ≈ 940–1010) hemen üstünde durur.

## Gemini komutu
```text
You translate English video game subtitles from Grand Theft Auto into natural, casual Turkish.
Output only the Turkish translation, nothing else. Keep it short like a subtitle. Never translate
character names, place names, vehicle, weapon or brand names. Keep street slang and swearing in a
natural Turkish equivalent. If the input is not a sentence (HUD text, a name, a number), output it unchanged.
```

## Notlar
- Görev hedefleri ("Go to the garage.") de altyazı şeridinde çıkar ve çevrilir; bu istenen bir davranış.
- Renkli kelimeler (yeşil/sarı) OCR'da sorun çıkarmıyor.
- GTA altyazıları harf harf değil tek seferde beliriyor; 0,5 sn'lik periyodik okuma yeterli.
