# GTA V altyazi filtresi (AltyaziTV icin).
# OCR kutusundaki her seyi degil, yalnizca diyalog/gorev cumlesine benzeyen satirlari gecirir.
# Bos metin donerse Luna o okumayi cevirmez.
import re

# Satir en az bu kadar kelime ve harf icermeli (tabela, arac adi, "Grove St." gibi kirintilar elensin)
MIN_KELIME = 3
MIN_HARF = 10
# Harflerin, bosluk haric karakterlere orani (HUD, sayi, para, sembol yiginlarini eler)
MIN_HARF_ORANI = 0.7

_harf = re.compile(r"[A-Za-z]")
_kucuk = re.compile(r"[a-z]")
_kelime = re.compile(r"[A-Za-z][A-Za-z'\-]*")
# Mesafe (1.2mi, 300m), saat (12:45), para ($25,000): harita/HUD yazilari
_hud = re.compile(r"\d+(?:[.,]\d+)?\s?(?:mi|km|m|ft)\b|\b\d{1,2}:\d{2}\b|\$\s?\d", re.I)


def _diyalog_mu(satir):
    if _hud.search(satir):
        return False
    harfler = len(_harf.findall(satir))
    if harfler < MIN_HARF:
        return False
    if len(_kelime.findall(satir)) < MIN_KELIME:
        return False
    if not _kucuk.search(satir):  # TAMAMI BUYUK HARF: HUD basliklari
        return False
    dolu = len(re.sub(r"\s", "", satir))
    return dolu and harfler / dolu >= MIN_HARF_ORANI


def POSTSOLVE(line):
    satirlar = [s.strip() for s in line.splitlines()]
    kalan = [s for s in satirlar if s and _diyalog_mu(s)]
    return " ".join(kalan)
