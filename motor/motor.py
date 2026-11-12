"""Altyazi motoru: ekrani biz okuruz, konumlu Turkce yayini biz yapariz; Luna arka planda OCR + ceviri servisi.

  her bolge (alt altyazi, sol ust ipucu kutusu):
    ekran seridi -> golgeli on isleme -> Luna /api/ocr (Snipping Tool OCR, satir kutulariyla) -> dengeleyici
    -> Luna /api/translate (mypost filtresi, onbellek, oyun paketi, Gemini)
    -> ws :2333  /api/ws/olay: Turkce + Ingilizcenin ekrandaki kutusu (TV ve OBS tam ustune siyah zeminle yazar)
                 /api/ws/text/trans: eski bicim, yalniz altyazinin Turkcesi

Neden: Luna kareyi oldugu gibi okuyor; arka plan karisinca "vou", "cloc clock" gibi bozuk satirlar ve plaka/HUD
gibi altyazi olmayan yazilar geliyordu. Golgeli on isleme + kare tabanli dengeleyiciyle kayittaki 80 sn'lik
konusmada her satir tam bir kez ve dogru okundu (olcum: README). Luna ayrica yalniz metni yayinliyordu; Ingilizce
yazinin YERINI bilmeden ustune yazilamaz.

Luna'nin kendi OCR dongusu KAPALI ve yayini 2335'te olmali (2333 motorun): python motor.py --luna-kur

  python motor.py                                   ekrandan canli
  python motor.py --video kayit.mkv --bas 160 --sure 60     kayittan (1080p kayit)
  python motor.py ... --kuru                        Luna'ya cevirtme, yalniz okunanlari yaz
  python motor.py --luna-kur | --luna-geri          Luna'yi motora gore ayarla / eski haline dondur (Luna kapaliyken)
"""
import argparse
import base64
import io
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

import numpy as np

KLASOR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KLASOR)
import onisleme  # noqa: E402
from dengeleyici import Dengeleyici  # noqa: E402

AYAR_DOSYASI = os.path.join(KLASOR, "motor_ayar.json")  # git'e girmez (ekran koordinatlari)
VARSAYILAN = {
    # 4K ekranda okuma bolgeleri [x, y, genislik, yukseklik] (fiziksel piksel)
    "bolgeler": {
        # Alt altyazi: Luna'nin eski bolgesinden ~45 px asagi (ikinci satir sinira tasiyordu), sol kenar mini
        # haritanin sag kenarindaki noktalardan uzak (satir basina ": " yapisiyordu)
        "alt": {"kutu": [811, 1689, 2201, 370], "on_isleme": "golgeli"},
        # Sol ust gorev/ipucu kutusu (koyu yari saydam kutuda golgesiz ince beyaz yazi; 5 satira kadar uzayabilir).
        # Golgeli on isleme bu ince yaziyi bozuyor ("Stugio", "atcess"), ham okuma kusursuz. Kutu yokken okunan
        # tabela/sokak yazilarini Luna'nin filtresi atar. Nadiren degisir: her 2 karede bir okunur.
        "ipucu": {"kutu": [180, 62, 1066, 478], "on_isleme": "ham", "her_kac_karede": 2},
    },
    "aralik_sn": 0.25,
    "luna": "http://127.0.0.1:2335",
    "luna_cevirici": "selfbuild",
    "yayin_portu": 2333,
    "luna_klasoru": os.path.join(os.path.expanduser("~"), "LunaTranslator"),
}
LUNA_PORTU = 2335
BOS_PIKSEL = 60       # on islemeden sonra bu kadar yazi pikselinden az: yazi yok, OCR'a gonderme
AYNI_MASKE = 0.02     # yazi maskesi oncekinden bu orandan az degistiyse ayni yazi: tekrar OCR yapma
log = logging.getLogger("motor")


def ayar_yukle():
    a = json.loads(json.dumps(VARSAYILAN))
    try:
        with open(AYAR_DOSYASI, encoding="utf-8") as f:
            ozel = json.load(f)
        bolgeler = ozel.pop("bolgeler", {})
        a.update(ozel)
        for ad, b in bolgeler.items():
            a["bolgeler"].setdefault(ad, {}).update(b)
    except (OSError, ValueError):
        pass
    return a


# ---------------------------------------------------------------- metin duzeltmeleri (OCR -> cumle)
# Ikili goruntude virgulun kuyrugu kaybolur: "Hey. how" -> "Hey, how" (ama "..." uc noktaya dokunma)
_VIRGUL = re.compile(r"(?<!\.)\.(\s+)(?=[a-z])")
_KESME = re.compile(r"\b(I|you|we|they|he|she|it|that|there|who|what|where|let|don|can|won|isn|didn|doesn|wasn)"
                    r" (m|re|ll|ve|d|s|t)\b", re.I)  # kesme isareti kaybolur: "I m" -> "I'm"
_BAS_KIRINTI = re.compile(r"^[^\w\"'“‘(¿¡]+")  # satir basina yapisan kirintilar


def duzelt(metin):
    return _BAS_KIRINTI.sub("", _KESME.sub(r"\1'\2", _VIRGUL.sub(r",\1", metin))).strip()


# ---------------------------------------------------------------- Luna (arka plan servisi)
def _istek(url, veri=None, zaman_asimi=10):
    istek = urllib.request.Request(url, data=veri, headers={"Content-Type": "application/json"} if veri else {})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
        return r.read()


def ocr(luna, rgb):
    """Donus: (metin, kutu) — kutu satir kutularinin birlesimi [x0, y0, x1, y1] (goruntu pikseli) ya da None."""
    from PIL import Image
    tampon = io.BytesIO()
    Image.fromarray(rgb).save(tampon, "PNG", compress_level=1)
    veri = json.dumps({"image": base64.b64encode(tampon.getvalue()).decode()}).encode()
    sonuc = json.loads(_istek(luna + "/api/ocr", veri))
    satirlar = [s for s in (sonuc.get("results") or []) if (s.get("text") or "").strip()]
    if not satirlar:
        return "", None
    satirlar.sort(key=lambda s: min(p["y"] for p in s["box"]))
    xs = [p["x"] for s in satirlar for p in s["box"]]
    ys = [p["y"] for s in satirlar for p in s["box"]]
    return " ".join(s["text"].strip() for s in satirlar), [min(xs), min(ys), max(xs), max(ys)]


def cevir(ayar, metin):
    """Luna /api/translate: mypost filtresi + selfbuild (onbellek, oyun paketi, Gemini). Filtre reddederse ''."""
    url = "%s/api/translate?id=%s&text=%s" % (ayar["luna"], ayar["luna_cevirici"], urllib.parse.quote(metin))
    sonuc = json.loads(_istek(url, zaman_asimi=12) or b"{}")
    return (sonuc.get("result") or "").strip()


def luna_ayarla(ayar, motorla):
    """Luna KAPALIYKEN (acikken kapanista eski ayari geri yazar). motorla=True: kendi OCR dongusu kapali, yayin
    portu 2335 (2333 motorun). False: eski duzen (Luna okur ve 2333'ten yayinlar; okuma bolgesi geri konur)."""
    yol = os.path.join(ayar["luna_klasoru"], "userconfig", "config.json")
    with open(yol, encoding="utf-8") as f:
        c = json.load(f)
    shutil.copy2(yol, yol + ".bak_motor")
    c["sourcestatus2"]["ocr"]["use"] = not motorla
    c["networktcpport"] = LUNA_PORTU if motorla else 2333
    if not motorla and not c.get("ocrregions2"):
        c["ocrregions2"] = [[771, 1689, 2241, 324]]
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=4)
    print("Luna: OCR dongusu %s, yayin portu %d (yedek: config.json.bak_motor)" % (
        "KAPALI" if motorla else "ACIK", c["networktcpport"]))


# ---------------------------------------------------------------- ceviri + yayin (bolge basina is parcacigi)
class Cevirmen:
    """Okuma dongusunu bekletmeden cevirir ve yayinlar. Bolge basina sira: altyazi Gemini'yi beklerken ipucu
    kutusu takilmaz. Ceviri gelmeden ayni bolgede yeni bir satir okunduysa eski sonuc atilir (eskimis)."""

    def __init__(self, ayar, yayinci, kuru=False):
        self.ayar, self.yayinci, self.kuru = ayar, yayinci, kuru
        self.onbellek = {}  # metin -> ceviri (geri gelen satir Luna'ya sorulmadan)
        self.surum, self.kuyruklar = {}, {}

    def _kuyruk(self, bolge):
        if bolge not in self.kuyruklar:
            self.kuyruklar[bolge] = queue.Queue()
            threading.Thread(target=self._isci, args=(bolge,), daemon=True).start()
        return self.kuyruklar[bolge]

    def olay(self, bolge, tur, metin, kutu):
        if tur == "temizle":
            if bolge != "alt":  # altyazi gitse de gec gelen cevirisi okuma suresince gosterilir; ipucu kutusu gidince yok
                self.surum[bolge] = self.surum.get(bolge, 0) + 1
            if self.yayinci:
                self.yayinci.gonder({"tur": "gizle", "bolge": bolge})
            return
        self.surum[bolge] = self.surum.get(bolge, 0) + 1
        self._kuyruk(bolge).put((self.surum[bolge], metin, kutu))

    def _isci(self, bolge):
        while True:
            surum, metin, kutu = self.kuyruklar[bolge].get()
            if surum != self.surum.get(bolge):
                continue  # siradayken eskidi
            t0 = time.monotonic()
            tr = self.onbellek.get(metin)
            if tr is None and not self.kuru:
                try:
                    tr = cevir(self.ayar, metin)
                except Exception as e:
                    log.warning("ceviri alinamadi (Luna acik mi?): %s", e)
                    tr = ""
                if tr:
                    self.onbellek[metin] = tr
            if surum != self.surum.get(bolge):
                log.info("%-6s eskidi, gosterilmedi: %s", bolge, metin[:60])
                continue
            log.info("%-6s %4.0f ms  %s  =>  %s", bolge, (time.monotonic() - t0) * 1000, metin[:70], (tr or "-")[:70])
            if tr and self.yayinci:
                self.yayinci.gonder({"tur": "goster", "bolge": bolge, "kutu": kutu, "tr": tr, "en": metin})


# ---------------------------------------------------------------- kaynaklar
def xbox_aktif():
    """Xbox uzaktan oynatma sesi akiyor mu. Akmiyorsa ekranda oyun yok: masaustundeki koyu zemin + beyaz yazi
    (VS Code, tarayici) golgeli on islemeden gecip TV'ye/yayina gitmesin diye o sirada hic okunmaz."""
    try:
        from pycaw.pycaw import AudioUtilities
    except ImportError:
        return True
    for s in AudioUtilities.GetAllSessions():
        try:
            if s.Process and s.Process.name().lower() == "xboxpcapp.exe" and s.State == 1:
                return True
        except Exception:
            continue
    return False


def ekran_kaynagi(ayar):
    """(t, {bolge: (rgb, x0, y0)}, olcek, (ekran_gen, ekran_yuk)); oyun yokken kareler None."""
    import mss
    aktif, son_kontrol = False, 0.0
    with mss.MSS() as m:
        ekran = (m.monitors[1]["width"], m.monitors[1]["height"])
        olcek = ekran[1] / 1080.0
        while True:
            if time.monotonic() - son_kontrol >= 2:
                yeni = xbox_aktif()
                if yeni != aktif:
                    log.info("uzaktan oynatma %s", "basladi: ekran okunuyor" if yeni else "yok: okuma durdu")
                aktif, son_kontrol = yeni, time.monotonic()
            if not aktif:
                yield time.monotonic(), None, olcek, ekran
                time.sleep(1)
                continue
            t = time.monotonic()
            kareler = {}
            for ad, b in ayar["bolgeler"].items():
                x, y, w, h = b["kutu"]
                kare = np.asarray(m.grab({"left": x, "top": y, "width": w, "height": h}))[..., 2::-1]  # BGRA->RGB
                kareler[ad] = (np.ascontiguousarray(kare), x, y)
            yield t, kareler, olcek, ekran
            time.sleep(max(0.0, ayar["aralik_sn"] - (time.monotonic() - t)))


def video_kaynagi(yol, bas, sure, ayar, hizli):
    """1080p kayit: bolgeler 4K bolgelerinin yarisi (olcek 1)."""
    fps = 1.0 / ayar["aralik_sn"]
    W, H = 1920, 1080
    surec = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(bas), "-t", str(sure),
                              "-i", yol, "-vf", "fps=%g,scale=%d:%d" % (fps, W, H), "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    t0, i = time.monotonic(), 0
    while True:
        ham = surec.stdout.read(W * H * 3)
        if len(ham) < W * H * 3:
            break
        tam = np.frombuffer(ham, np.uint8).reshape(H, W, 3)
        kareler = {}
        for ad, b in ayar["bolgeler"].items():
            x, y, w, h = [int(v / 2) for v in b["kutu"]]
            kareler[ad] = (np.ascontiguousarray(tam[y:y + h, x:x + w]), x, y)
        if not hizli:
            time.sleep(max(0.0, t0 + i / fps - time.monotonic()))
        yield bas + i / fps, kareler, 1.0, (W, H)
        i += 1


# ---------------------------------------------------------------- dongu
class _Bolge:
    def __init__(self, ad, ayar_b):
        on_isleme = ayar_b.get("on_isleme", "golgeli")
        self.ad, self.on_isleme = ad, onisleme.ON_ISLEMELER[on_isleme]
        self.ikili = on_isleme in onisleme.IKILI
        self.her_kac = max(1, int(ayar_b.get("her_kac_karede", 1)))
        self.deng = Dengeleyici()
        self.maske, self.metin, self.kutu = None, "", None

    def oku(self, ayar, kare, olcek, sayac):
        """Donus: (metin, kutu_goruntu_pikseli)."""
        hazir = self.on_isleme(kare, olcek)
        maske = (hazir[..., 0] == 0) if self.ikili else onisleme.parlak_maske(kare)
        if maske.sum() < BOS_PIKSEL * olcek * olcek:
            self.maske, self.metin, self.kutu = maske, "", None
        elif self.maske is not None and self.maske.shape == maske.shape and \
                (maske ^ self.maske).sum() <= AYNI_MASKE * max(1, maske.sum()):
            pass  # yazi degismedi (arka plan degisse de): OCR'a gitme
        else:
            t0 = time.monotonic()
            metin, kutu = ocr(ayar["luna"], hazir)
            sayac["ocr"] += 1
            sayac["ocr_ms"] += (time.monotonic() - t0) * 1000
            self.maske, self.metin, self.kutu = maske, duzelt(metin), kutu
        return self.metin, self.kutu


def calis(kaynak, ayar, cevirmen):
    bolgeler = {ad: _Bolge(ad, b) for ad, b in ayar["bolgeler"].items()}
    sayac = {"kare": 0, "ocr": 0, "ocr_ms": 0.0, "satir": 0}
    son_ozet = time.monotonic()
    for t, kareler, olcek, (W, H) in kaynak:
        if kareler is None:  # oyun yok: ekranda ne varsa temizlensin
            for b in bolgeler.values():
                for tur, m in b.deng.adim(t, ""):
                    cevirmen.olay(b.ad, tur, m, None)
                b.maske, b.metin, b.kutu = None, "", None
            continue
        sayac["kare"] += 1
        for ad, (kare, x0, y0) in kareler.items():
            b = bolgeler[ad]
            if sayac["kare"] % b.her_kac:
                continue
            try:
                metin, kutu = b.oku(ayar, kare, olcek, sayac)
            except Exception as e:
                log.warning("OCR yapilamadi (Luna acik mi?): %s", e)
                time.sleep(2)
                continue
            # Ekran orani (0-1): TV ve OBS kendi cozunurlugune cevirir
            oran = None if kutu is None else [round((x0 + kutu[0]) / W, 4), round((y0 + kutu[1]) / H, 4),
                                               round((kutu[2] - kutu[0]) / W, 4), round((kutu[3] - kutu[1]) / H, 4)]
            for tur, m in b.deng.adim(t, metin):
                log.info("%-6s %-8s %s", ad, tur, m or "")
                if tur != "temizle":
                    sayac["satir"] += 1
                cevirmen.olay(ad, tur, m, oran)
        if time.monotonic() - son_ozet >= 60:
            log.info("ozet: %d kare, %d OCR (ort %.0f ms), %d satir", sayac["kare"], sayac["ocr"],
                     sayac["ocr_ms"] / max(1, sayac["ocr"]), sayac["satir"])
            son_ozet = time.monotonic()
    return sayac


def _tek_ornek():
    import ctypes
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\xbox-samsung-subtitles-tv-motor")
    return ctypes.windll.kernel32.GetLastError() != 183


def main(argv=None):
    ap = argparse.ArgumentParser(description="Altyazi motoru")
    ap.add_argument("--video")
    ap.add_argument("--bas", type=float, default=0)
    ap.add_argument("--sure", type=float, default=60)
    ap.add_argument("--hizli", action="store_true", help="videoyu gercek zamanli degil, hizli oynat")
    ap.add_argument("--kuru", action="store_true", help="Luna'ya cevirtme, yalniz okunanlari yaz")
    ap.add_argument("--yayinsiz", action="store_true", help="WebSocket yayini acma (deneme)")
    ap.add_argument("--luna-kur", action="store_true", help="Luna'yi motora gore ayarla (Luna kapaliyken)")
    ap.add_argument("--luna-geri", action="store_true", help="Luna'yi eski duzene dondur (Luna kapaliyken)")
    arg = ap.parse_args(argv)
    ayar = ayar_yukle()
    if arg.luna_kur or arg.luna_geri:
        return luna_ayarla(ayar, arg.luna_kur)
    isleyiciler = [logging.FileHandler(os.path.join(KLASOR, "motor.log"), encoding="utf-8")]
    if sys.stdout:
        isleyiciler.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S", handlers=isleyiciler)
    if not arg.video and not _tek_ornek():
        log.info("motor zaten calisiyor")
        return
    yayinci = None
    if not arg.yayinsiz:
        from yayinci import Yayinci
        # /api/textinput denemeleri: konumu bilinmeyen satir, altyazinin olagan yerinde gosterilsin
        yayinci = Yayinci(ayar["yayin_portu"],
                          girdi=lambda m: cevirmen.olay("alt", "yeni", m, [0.25, 0.87, 0.5, 0.065]))
    cevirmen = Cevirmen(ayar, yayinci, arg.kuru)
    kaynak = video_kaynagi(arg.video, arg.bas, arg.sure, ayar, arg.hizli) if arg.video else ekran_kaynagi(ayar)
    log.info("motor basladi (%s, bolgeler: %s, yayin: %s)", "video" if arg.video else "ekran",
             ", ".join("%s %s" % (ad, b["kutu"]) for ad, b in ayar["bolgeler"].items()),
             "yok" if yayinci is None else ":%d" % ayar["yayin_portu"])
    s = calis(kaynak, ayar, cevirmen)
    time.sleep(3)  # son cevirilerin bitmesi
    log.info("bitti: %d kare, %d OCR (ort %.0f ms), %d satir", s["kare"], s["ocr"], s["ocr_ms"] / max(1, s["ocr"]),
             s["satir"])


if __name__ == "__main__":
    main()
