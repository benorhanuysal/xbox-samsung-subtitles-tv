"""Altyazi dengeleyici: kare kare OCR okumalarindan "yeni satir / satir buyudu / satir gitti" olaylari uretir.
Luna'nin metin tabanli 8 sn tekrar kuralinin yerine kare tabanli karar (fikir CouchSubs'tan, kod bizim):
- Yeni satir, iki okuma ust uste benzer cikinca ya da cumle isaretiyle (. ! ? …) bitince gonderilir.
- Ekranda duran satir tekrar gonderilmez; ayni satirin daha kotu yeniden okumasi yok sayilir.
- Satir buyurse (yarim okunmustu, tamami geldi) "degistir" olarak tekrar gonderilir.
- BOS_SN boyunca bos okunursa satir ekrandan cikmis sayilir ("temizle"); GERI_SN icinde ayni satir
  geri gelirse beklemeden gonderilir.
Saf mantik: zaman disaridan verilir, cevrimdisi kayitlarla test edilebilir."""
import re
from difflib import SequenceMatcher

BENZER = 0.85      # iki okuma ayni aday satir mi (harf dizisi benzerligi)
# Ekranda oldugu bilinen satirla karsilastirirken daha gevsek: kisa satirda 2 OCR hatasi bile 0.85'in altina
# dusurur ve nokta ile bittigi icin hemen "yeni" sayilip ayni satir tekrar gonderilirdi
BENZER_EKRANDAKI = 0.75
BUYUME = 1.15      # yeni okuma bu kadar uzunsa ve eskisiyle basliyorsa satir buyumus demek
GEREKEN_OKUMA = 2  # cumle sonu isareti yoksa ust uste bu kadar benzer okuma
BOS_SN = 0.8
GERI_SN = 1.5
_CUMLE_SONU = re.compile(r"[.!?…]['\"”’)]?\s*$")


def sade(metin):
    return re.sub(r"[^a-z0-9]", "", (metin or "").lower())


def benzer(a, b, esik=BENZER):
    a, b = sade(a), sade(b)
    return bool(a) and bool(b) and SequenceMatcher(None, a, b).ratio() >= esik


def buyudu_mu(yeni, eski):
    """yeni, eski satirin uzamis hali mi (daktilo gibi yazilan ya da yarim okunan satir tamamlandi)."""
    a, b = sade(eski), sade(yeni)
    if not a or len(b) < BUYUME * len(a):
        return False
    return SequenceMatcher(None, a, b[:len(a)]).ratio() >= BENZER


def cumle_bitti_mi(metin):
    return bool(_CUMLE_SONU.search(metin or ""))


class Dengeleyici:
    def __init__(self):
        self.gonderilen = ""        # ekranda oldugu bilinen (gonderilmis) satir
        self.aday, self.aday_sayisi = "", 0
        self.bos_baslangic = None
        self.gecmis = []            # [(satir, ekrandan_cikma_zamani)]

    def adim(self, t, metin):
        """Bir okuma (t saniye, metin; bos = altyazi yok). Donus: olay listesi [(tur, metin)]."""
        metin = (metin or "").strip()
        if not metin:
            return self._bos(t)
        self.bos_baslangic = None
        if self.gonderilen and benzer(metin, self.gonderilen, BENZER_EKRANDAKI) \
                and not buyudu_mu(metin, self.gonderilen):
            self.aday, self.aday_sayisi = "", 0
            return []  # ayni satir hala ekranda (ya da daha kotu okunmus hali)
        if self.gonderilen and buyudu_mu(metin, self.gonderilen):
            self.gonderilen = metin
            return [("degistir", metin)]
        # Yeni bir satir adayi
        if self.aday and (benzer(metin, self.aday) or buyudu_mu(metin, self.aday)):
            self.aday_sayisi += 1
            if len(sade(metin)) >= len(sade(self.aday)):
                self.aday = metin  # daha uzun/tam okumayi tut
        else:
            self.aday, self.aday_sayisi = metin, 1
        geri_geldi = any(benzer(metin, s) and t - cikis <= GERI_SN for s, cikis in self.gecmis)
        if self.aday_sayisi >= GEREKEN_OKUMA or cumle_bitti_mi(metin) or geri_geldi:
            olaylar = []
            if self.gonderilen:
                self._gecmise(self.gonderilen, t)
            self.gonderilen = self.aday
            self.aday, self.aday_sayisi = "", 0
            olaylar.append(("yeni", self.gonderilen))
            return olaylar
        return []

    def _bos(self, t):
        self.aday, self.aday_sayisi = "", 0
        if not self.gonderilen:
            return []
        if self.bos_baslangic is None:
            self.bos_baslangic = t
            return []
        if t - self.bos_baslangic >= BOS_SN:
            self._gecmise(self.gonderilen, t)
            self.gonderilen, self.bos_baslangic = "", None
            return [("temizle", None)]
        return []

    def _gecmise(self, satir, t):
        self.gecmis = [(s, c) for s, c in self.gecmis if t - c <= GERI_SN] + [(satir, t)]
