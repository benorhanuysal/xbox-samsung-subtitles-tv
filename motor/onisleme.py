"""Altyazi seridi icin OCR on islemeleri (numpy). GTA altyazisi: beyaz/acik gri yazi + sag-asagida koyu golge.
Arka plan (yol, gokyuzu, araba) karisinca OCR kelimeleri bozuyor ("vou", "cloc clock"); burada yaziyi
arka plandan ayiklayip "beyaz zemin uzerinde siyah yazi" haline getiriyoruz (OCR'in en iyi okudugu bicim).
Fikir CouchSubs'tan (gölge ile yazi ayiklama, otomatik seviye); kod bizim.

Hepsi girdi olarak RGB uint8 dizi (y, x, 3) ve olcek alir (1.0 = 1080p ekran; 4K ekran = 2.0: golge ve harf
kalinligi piksel olarak buyur), ayni boyutta RGB uint8 dondurur."""
import numpy as np

BEYAZ_EN_AZ = 175      # yazi pikseli: en karanlik kanal bile bu kadar parlak
BEYAZ_RENK_FARKI = 45  # ve neredeyse renksiz (kanallar arasi fark kucuk)
GOLGE_ESIK = 70        # golge pikseli: parlaklik bunun altinda
GOLGE_EN_UZAK = 3      # 1080p'de golge yaziya en fazla bu kadar piksel uzakta (olcekle buyur)


def _genislet(maske, yaricap):
    """Ikili maskeyi kare komsulukta yaricap kadar buyut (numpy kaydirmalariyla)."""
    sonuc = maske.copy()
    for _ in range(yaricap):
        onceki = sonuc.copy()
        sonuc[:, 1:] |= onceki[:, :-1]
        sonuc[:, :-1] |= onceki[:, 1:]
        sonuc[1:, :] |= onceki[:-1, :]
        sonuc[:-1, :] |= onceki[1:, :]
    return sonuc


def _parlaklik(rgb):
    r, g, b = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)
    return (r * 3 + g * 6 + b) // 10


def _maskeden(maske):
    """True = yazi -> siyah, digeri beyaz."""
    cikti = np.full(maske.shape + (3,), 255, np.uint8)
    cikti[maske] = 0
    return cikti


def beyaz(rgb, olcek=1.0):
    """Yalniz acik ve renksiz pikseller (yazi govdesi)."""
    rgb16 = rgb.astype(np.int16)
    en_az, en_cok = rgb16.min(axis=2), rgb16.max(axis=2)
    return _maskeden((en_az >= BEYAZ_EN_AZ) & (en_cok - en_az <= BEYAZ_RENK_FARKI))


def golgeli(rgb, olcek=1.0):
    """Acik renksiz piksel + sag-asagisinda koyu piksel = golgeli altyazi yazisi. Parlak gokyuzu, beyaz araba,
    plaka gibi golgesiz parlak alanlari eler. Golge testi yalniz harf kenarini yakalar; harf govdesi, bu
    kenarlara yakin acik pikseller alinarak geri doldurulur (yoksa buyuk yazida harflerin ici bosalir)."""
    rgb16 = rgb.astype(np.int16)
    en_az, en_cok = rgb16.min(axis=2), rgb16.max(axis=2)
    acik = (en_az >= BEYAZ_EN_AZ - 20) & (en_cok - en_az <= BEYAZ_RENK_FARKI + 15)
    koyu = _parlaklik(rgb) < GOLGE_ESIK
    golge = np.zeros_like(acik)
    h, w = acik.shape
    for k in range(1, max(GOLGE_EN_UZAK, round(GOLGE_EN_UZAK * olcek)) + 1):
        golge[:h - k, :w - k] |= koyu[k:, k:]
    kenar = acik & golge
    govde = _genislet(kenar, max(1, round(2 * olcek))) & acik
    return _maskeden(govde)


def seviye(rgb, olcek=1.0):
    """Otomatik seviye: en parlak %0,5 beyaza gerilir (soluk/kontrastsiz karelerde yaziyi belirginlestirir)."""
    p = _parlaklik(rgb)
    ust = max(1, int(np.percentile(p, 99.5)))
    alt = int(np.percentile(p, 5))
    gri = np.clip((p - alt) * 255 // max(1, ust - alt), 0, 255).astype(np.uint8)
    return np.repeat((255 - gri)[..., None], 3, axis=2)  # ters: koyu yazi acik zemin


def parlak_maske(rgb):
    """Ham okunan bolgelerde (ipucu kutusu) "yazi var mi / degisti mi" icin: acik ve renksiz pikseller.
    OCR'a bu maske degil, ham goruntu gider."""
    rgb16 = rgb.astype(np.int16)
    en_az, en_cok = rgb16.min(axis=2), rgb16.max(axis=2)
    return (en_az >= 160) & (en_cok - en_az <= 50)


ON_ISLEMELER = {"ham": lambda rgb, olcek=1.0: rgb, "beyaz": beyaz, "golgeli": golgeli, "seviye": seviye}
# Bu on islemelerin ciktisi zaten "beyaz zemin ustunde siyah yazi": maske ciktidan okunur
IKILI = {"beyaz", "golgeli"}
