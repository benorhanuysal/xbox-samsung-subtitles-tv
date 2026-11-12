# GTA V altyazi filtresi (AltyaziTV icin).
# OCR kutusundaki her seyi degil, yalnizca diyalog/gorev cumlesine benzeyen satirlari gecirir.
# Bos metin donerse Luna o okumayi cevirmez.
import re

# Satir en az bu kadar kelime ve harf icermeli (tabela, arac adi, "Grove St." gibi kirintilar elensin)
MIN_KELIME = 3
MIN_HARF = 10
# . ! ? ile biten kisa replikler ("Shut up!", "Get in.") icin daha dusuk sinir
MIN_KELIME_CUMLE = 2
MIN_HARF_CUMLE = 6
# Harflerin, bosluk haric karakterlere orani (HUD, sayi, para, sembol yiginlarini eler)
MIN_HARF_ORANI = 0.7

_harf = re.compile(r"[A-Za-z]")
_kucuk = re.compile(r"[a-z]")
_kelime = re.compile(r"[A-Za-z][A-Za-z'\-]*")
# Mesafe (1.2mi, 300m), saat (12:45), para ($25,000): harita/HUD yazilari
_hud = re.compile(r"\d+(?:[.,]\d+)?\s?(?:mi|km|m|ft)\b|\b\d{1,2}:\d{2}\b|\$\s?\d", re.I)
# Oyuncu/gamertag adlari (parker994, YT55, A7md256Y) ve sokak adi ayiraci "|"
_etiket = re.compile(r"[A-Za-z]+\d{2,}|[A-Za-z]\d[A-Za-z]|\|")
# Kaynak Ingilizce: bu harfler varsa metin zaten Turkce (Xbox bildirimi, baska pencere)
_turkce = re.compile(r"[ğĞışŞİ]")
# Harflerin cogu BUYUK ise tabela/baslik ("CASINO & RESORT", "... INVITED")
MAX_BUYUK_ORANI = 0.5
# PC'deki baska pencerelerin yazilari (okuma bolgesinin ustune gelirse)
_pc = re.compile(r"ctrl\s*esc|unfocus|Queue another message|Ask Claude to edit|Thought for \d+s|Esc to cancel", re.I)
# Kumanda tusu adlari gecen satir kontrol ipucudur ("Zoom LT RT Select Blip")
_tus = re.compile(r"\b(?:LT|RT|LB|RB|LS|RS)\b.*\b(?:LT|RT|LB|RB|LS|RS)\b|\b(?:Zoom|Move Camera|Select Blip)\b")
# Olum/menu ekranindaki kontrol ipuclari ("Passive Mode  Y  Respawn  A  Start ...")
# OCR kelimeleri bitistirir/bozar ("VRespawn", "Besnawn", "Dassive Mode"): kelime siniri aranmaz
_ipucu = re.compile(r"s[pn]awn|[PD]assive Mode|Spectate|Quick Restart|Quick GPS|\bPress\s+\S{1,2}\s+to\b", re.I)
# Tus simgeleri OCR'da tek basina BUYUK harf olarak okunur (Y, V, B, R...). Ingilizcede tek basina
# duran buyuk harf yalnizca "I" ve "A". Kucuk harfe bakilmaz: OCR kesme isaretini kacirinca "it s" olur.
# Tek bir tane yetmez: diyalogda "Mr. F", "Plan B" gecer; en az iki tane varsa kontrol ipucudur.
_tek_harf = re.compile(r"(?<![A-Za-z'\-])[B-HJ-Z](?![A-Za-z'\-])")
EN_FAZLA_TEK_HARF = 1
# Gercek cumlelerde bu kucuk kelimeler bol; kamera/kontrol ipuclari ("Zoom LT Move Camera",
# "Low Detail R Select Blip") ve OCR copunde hic ya da cok az var.
_baglac = set("""a an the i you he she it we they me him her us them my your his its our their this that
to of in on at for with from by about as and or but so if not no is are was were be been am do does did
have has had will would can could should what who where when why how get got go just all there here
up out""".split())
MIN_BAGLAC_ORANI = 0.15


def _diyalog_mu(satir):
    if _hud.search(satir) or _etiket.search(satir) or _turkce.search(satir) or _pc.search(satir) or _tus.search(satir):
        return False
    if _ipucu.search(satir) or len(_tek_harf.findall(satir)) > EN_FAZLA_TEK_HARF:
        return False
    kelimeler = [k for k in _kelime.findall(satir) if not (len(k) > 1 and k.isupper())]  # "IT", "RT" sayilmaz
    # "You're" -> "you"
    if sum(k.lower().split("'")[0] in _baglac for k in kelimeler) < MIN_BAGLAC_ORANI * max(1, len(kelimeler)):
        return False
    buyuk = len(re.findall(r"[A-Z]", satir))
    if buyuk > MAX_BUYUK_ORANI * max(1, len(_harf.findall(satir))):
        return False
    harfler = len(_harf.findall(satir))
    cumle = satir.rstrip().endswith((".", "!", "?"))
    if harfler < (MIN_HARF_CUMLE if cumle else MIN_HARF):
        return False
    if len(_kelime.findall(satir)) < (MIN_KELIME_CUMLE if cumle else MIN_KELIME):
        return False
    if not _kucuk.search(satir):  # TAMAMI BUYUK HARF: HUD basliklari
        return False
    dolu = len(re.sub(r"\s", "", satir))
    return dolu and harfler / dolu >= MIN_HARF_ORANI


# Cumle sonuna yapisan kisa BUYUK harf kirintisi ("... other players. EVE"): arka plandaki tabela/HUD
_son_kirinti = re.compile(r"([.!?])\s+[A-Z\-]{1,5}$")

# Ayni altyazi ekranda dururken OCR her 0.3 sn'de biraz farkli okur ("plavers"/"players"); her okuma
# ayri ceviri olarak TV'ye gidince altyazi titrer. Bu sure icinde benzer metin tekrar gonderilmez.
TEKRAR_SN = 8
BENZERLIK = 0.75
# Kismen okunmus satirin tamami gelirse (belirgin uzunsa) yine gonderilir
UZAMA = 1.25
_son = {"metin": "", "zaman": 0.0}


def _sade(metin):
    return re.sub(r"[^a-z]", "", metin.lower())


def _tekrar_mi(metin):
    import time
    from difflib import SequenceMatcher
    simdi = time.time()
    a, b = _sade(_son["metin"]), _sade(metin)
    tekrar = (simdi - _son["zaman"] < TEKRAR_SN and a and b and len(b) < UZAMA * len(a)
              and SequenceMatcher(None, a, b).ratio() >= BENZERLIK)
    if not tekrar:
        _son["metin"] = metin
    _son["zaman"] = simdi  # ekranda durdukca sure uzar
    return tekrar


def POSTSOLVE(line):
    satirlar = [_son_kirinti.sub(r"\1", s.strip()) for s in line.splitlines()]
    kalan = [s for s in satirlar if s and _diyalog_mu(s)]
    metin = " ".join(kalan)
    if metin and _tekrar_mi(metin):
        return ""
    return metin
