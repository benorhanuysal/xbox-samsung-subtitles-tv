"""Altyazi motoru: ekrani biz okuruz, ceviri ve TV/OBS yayini Luna'da kalir.

  Ekran seridi -> golgeli on isleme -> Luna /api/ocr (Snipping Tool OCR) -> dengeleyici
      -> Luna /api/textinput -> mypost filtresi -> onbellek / oyun paketi / Gemini -> ws :2333 (TV, OBS)

Neden: Luna kareyi oldugu gibi okuyor; arka plan karisinca "vou", "cloc clock" gibi bozuk satirlar ve plaka/HUD
gibi altyazi olmayan yazilar geliyordu. Golgeli on isleme (yalniz golgeli beyaz yazi) + kare tabanli dengeleyici
ile kayittaki 80 sn'lik konusmada her satir tam bir kez ve dogru okundu (olcum: motor/README.md).
Luna'nin kendi OCR dongusu KAPALI olmali, yoksa TV'ye iki akis gider: python motor.py --luna-ocr kapat

  python motor.py                                   ekrandan canli
  python motor.py --video kayit.mkv --bas 160 --sure 60 --olcek 1    kayittan (1080p kayit = olcek 1)
  python motor.py ... --kuru                        Luna'ya gondermeden olaylari yaz
  python motor.py --luna-ocr kapat|ac               Luna'nin kendi OCR dongusunu kapat/ac (Luna kapaliyken)
"""
import argparse
import base64
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
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
    # 4K ekranda okuma bolgesi [x, y, genislik, yukseklik] (fiziksel piksel). Luna'nin bolgesinden ~45 px
    # asagi uzatildi (iki satirli altyazinin alt satiri eski bolgenin sinirina tasiyordu); sol kenar 40 px
    # saga alindi (mini haritanin sag kenarindaki beyaz noktalar satir basina ": " diye yapisiyordu).
    "bolge": [811, 1689, 2201, 370],
    "aralik_sn": 0.25,
    "luna": "http://127.0.0.1:2333",
    "on_isleme": "golgeli",
    "luna_klasoru": os.path.join(os.path.expanduser("~"), "LunaTranslator"),
}
BOS_PIKSEL = 60       # on islemeden sonra bu kadar yazi pikselinden az: altyazi yok, OCR'a gonderme
AYNI_MASKE = 0.02     # yazi maskesi oncekinden bu orandan az degistiyse ayni yazi: tekrar OCR yapma
log = logging.getLogger("motor")


def ayar_yukle():
    a = dict(VARSAYILAN)
    try:
        with open(AYAR_DOSYASI, encoding="utf-8") as f:
            a.update(json.load(f))
    except (OSError, ValueError):
        pass
    return a


# ---------------------------------------------------------------- metin duzeltmeleri (OCR -> cumle)
# Ikili goruntude virgulun kuyrugu kaybolur: "Hey. how" -> "Hey, how" (ama "..." uc noktaya dokunma)
_VIRGUL = re.compile(r"(?<!\.)\.(\s+)(?=[a-z])")
_KESME = re.compile(r"\b(I|you|we|they|he|she|it|that|there|who|what|where|let|don|can|won|isn|didn|doesn|wasn)"
                    r" (m|re|ll|ve|d|s|t)\b", re.I)  # kesme isareti kaybolur: "I m" -> "I'm"
_BAS_KIRINTI = re.compile(r"^[^\w\"'“‘(¿¡]+")  # satir basina yapisan ": " gibi kirintilar (telefon cercevesi vb.)


def duzelt(metin):
    return _BAS_KIRINTI.sub("", _KESME.sub(r"\1'\2", _VIRGUL.sub(r",\1", metin))).strip()


# ---------------------------------------------------------------- Luna
def _istek(url, veri=None, zaman_asimi=10):
    istek = urllib.request.Request(url, data=veri, headers={"Content-Type": "application/json"} if veri else {})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
        return r.read()


def ocr(luna, rgb):
    from PIL import Image
    tampon = io.BytesIO()
    Image.fromarray(rgb).save(tampon, "PNG", compress_level=1)
    veri = json.dumps({"image": base64.b64encode(tampon.getvalue()).decode()}).encode()
    sonuc = json.loads(_istek(luna + "/api/ocr", veri))
    satirlar = sorted(sonuc.get("results") or [], key=lambda s: min(p["y"] for p in s["box"]))
    return " ".join(s["text"].strip() for s in satirlar if (s.get("text") or "").strip())


def luna_gonder(luna, metin):
    _istek(luna + "/api/textinput?text=" + urllib.parse.quote(metin))


def luna_ocr_ayarla(ayar, acik):
    """Luna'nin kendi OCR dongusu (sourcestatus2.ocr.use). Luna KAPALIYKEN degistirilmeli: acikken kapanista
    eski ayari geri yazar. Acarken okuma bolgesini de geri koyar (Luna kapanista bazen siliyor)."""
    yol = os.path.join(ayar["luna_klasoru"], "userconfig", "config.json")
    with open(yol, encoding="utf-8") as f:
        c = json.load(f)
    shutil.copy2(yol, yol + ".bak_motor")
    c["sourcestatus2"]["ocr"]["use"] = bool(acik)
    if acik and not c.get("ocrregions2"):
        x, y, w, h = ayar["bolge"]
        c["ocrregions2"] = [[x, y, w, min(h, 324)]]
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=4)
    print("Luna OCR dongusu: %s (yedek: config.json.bak_motor)" % ("ACIK" if acik else "KAPALI"))


# ---------------------------------------------------------------- kaynaklar
def xbox_aktif():
    """Xbox uzaktan oynatma sesi akiyor mu. Akmiyorsa ekranda oyun yok: masaustundeki koyu zemin + beyaz yazi
    (VS Code, tarayici) golgeli on islemeden gecip TV'ye/yayina gitmesin diye o sirada hic okunmaz."""
    try:
        from pycaw.pycaw import AudioUtilities
    except ImportError:
        return True  # pycaw yoksa (baska kurulum) her zaman oku
    for s in AudioUtilities.GetAllSessions():
        try:
            if s.Process and s.Process.name().lower() == "xboxpcapp.exe" and s.State == 1:
                return True
        except Exception:
            continue
    return False


def ekran_kaynagi(ayar):
    import mss
    x, y, w, h = ayar["bolge"]
    aktif, son_kontrol = False, 0.0
    with mss.MSS() as m:
        olcek = m.monitors[1]["height"] / 1080.0
        while True:
            if time.monotonic() - son_kontrol >= 2:
                yeni = xbox_aktif()
                if yeni != aktif:
                    log.info("uzaktan oynatma %s", "basladi: ekran okunuyor" if yeni else "yok: okuma durdu")
                aktif, son_kontrol = yeni, time.monotonic()
            if not aktif:
                yield time.monotonic(), None, olcek  # dengeleyici "bos" gorsun (ekrandaki satir temizlensin)
                time.sleep(1)
                continue
            t = time.monotonic()
            kare = np.asarray(m.grab({"left": x, "top": y, "width": w, "height": h}))[..., 2::-1]  # BGRA -> RGB
            yield t, np.ascontiguousarray(kare), olcek
            time.sleep(max(0.0, ayar["aralik_sn"] - (time.monotonic() - t)))


def video_kaynagi(yol, bas, sure, olcek, ayar, hizli):
    """1080p kayitta bolge 4K bolgesinin yarisi (olcek 1)."""
    # ffmpeg yuv420p kayitta kesimi cift sayiya yuvarlar; boyutlar tutsun diye kendimiz cift yapiyoruz
    x, y, w, h = [int(v * olcek / 2.0) // 2 * 2 for v in ayar["bolge"]]
    fps = 1.0 / ayar["aralik_sn"]
    ham = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(bas), "-t", str(sure), "-i", yol,
                          "-vf", "fps=%g,crop=%d:%d:%d:%d" % (fps, w, h, x, y), "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-"], capture_output=True, check=True).stdout
    kareler = np.frombuffer(ham, np.uint8).reshape(-1, h, w, 3)
    t0 = time.monotonic()
    for i, k in enumerate(kareler):
        if not hizli:
            time.sleep(max(0.0, t0 + i / fps - time.monotonic()))
        yield bas + i / fps, k, olcek


# ---------------------------------------------------------------- dongu
def calis(kaynak, ayar, kuru=False):
    on_isleme = onisleme.ON_ISLEMELER[ayar["on_isleme"]]
    deng = Dengeleyici()
    onceki_maske, onceki_metin = None, ""
    sayac = {"kare": 0, "ocr": 0, "ocr_ms": 0.0, "yeni": 0}
    son_ozet = time.monotonic()
    for t, kare, olcek in kaynak:
        if kare is None:  # oyun yok
            for tur, m in deng.adim(t, ""):
                log.info("%-8s %s", tur, m or "")
            onceki_maske, onceki_metin = None, ""
            continue
        sayac["kare"] += 1
        hazir = on_isleme(kare, olcek)
        maske = hazir[..., 0] == 0
        if maske.sum() < BOS_PIKSEL * olcek * olcek:
            metin = ""
        elif onceki_maske is not None and onceki_maske.shape == maske.shape and \
                (maske ^ onceki_maske).sum() <= AYNI_MASKE * max(1, maske.sum()):
            metin = onceki_metin  # yazi degismedi (arka plan degisse de): OCR'a gitme
        else:
            t0 = time.monotonic()
            try:
                metin = duzelt(ocr(ayar["luna"], hazir))
            except Exception as e:
                log.warning("OCR yapilamadi (Luna acik mi?): %s", e)
                time.sleep(2)
                continue
            sayac["ocr"] += 1
            sayac["ocr_ms"] += (time.monotonic() - t0) * 1000
        onceki_maske, onceki_metin = maske, metin
        for tur, m in deng.adim(t, metin):
            log.info("%-8s %s", tur, m or "")
            if tur in ("yeni", "degistir"):
                sayac["yeni"] += 1
                if not kuru:
                    try:
                        luna_gonder(ayar["luna"], m)
                    except Exception as e:
                        log.warning("Luna'ya gonderilemedi: %s", e)
        if time.monotonic() - son_ozet >= 60:
            log.info("ozet: %d kare, %d OCR (ort %.0f ms), %d satir", sayac["kare"], sayac["ocr"],
                     sayac["ocr_ms"] / max(1, sayac["ocr"]), sayac["yeni"])
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
    ap.add_argument("--olcek", type=float, default=1.0, help="video kaynaginda: 1080p kayit = 1")
    ap.add_argument("--hizli", action="store_true", help="videoyu gercek zamanli degil, hizli oynat")
    ap.add_argument("--kuru", action="store_true", help="Luna'ya gonderme, yalniz olaylari yaz")
    ap.add_argument("--luna-ocr", choices=["kapat", "ac"])
    arg = ap.parse_args(argv)
    ayar = ayar_yukle()
    if arg.luna_ocr:
        return luna_ocr_ayarla(ayar, arg.luna_ocr == "ac")
    isleyiciler = [logging.FileHandler(os.path.join(KLASOR, "motor.log"), encoding="utf-8")]
    if sys.stdout:
        isleyiciler.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S", handlers=isleyiciler)
    if arg.video:
        kaynak = video_kaynagi(arg.video, arg.bas, arg.sure, arg.olcek, ayar, arg.hizli)
    else:
        if not _tek_ornek():
            log.info("motor zaten calisiyor")
            return
        kaynak = ekran_kaynagi(ayar)
    log.info("motor basladi (%s, on isleme: %s, bolge: %s)", "video" if arg.video else "ekran",
             ayar["on_isleme"], ayar["bolge"])
    s = calis(kaynak, ayar, arg.kuru)
    log.info("bitti: %d kare, %d OCR (ort %.0f ms), %d satir", s["kare"], s["ocr"], s["ocr_ms"] / max(1, s["ocr"]),
             s["yeni"])


if __name__ == "__main__":
    main()
