# LunaTranslator ozel cevirici (userconfig\selfbuild.py): Gemini ve Google yaristirilir.
# Luna bunu tek bir cevirici olarak gorur; TV'ye her cumle icin tek ceviri gider.
#  - Gemini anahtari girilmemisse yalnizca (ucretsiz) Google kullanilir.
#  - Cumle ayni anda hem Gemini'ye hem Google'a gonderilir.
#  - Gemini GEMINI_BEKLE saniye icinde donerse onun cevirisi (daha dogal), donmezse Google'inki kullanilir.
#    Olculen Gemini gecikmesi 0,6-6,8 sn arasi degisiyor; sirayla beklemek Google'dan bile yavas kaliyordu.
#  - 429 (istek siniri) sonrasi BEKLEME_SN boyunca Gemini hic denenmez.
#  - Anahtar, model ve komut Luna'daki "大模型通用接口" (chatgpt-3rd-party) ayarlarindan okunur.
#  - Her ceviri userconfig\altyazi_ceviri.log dosyasina yazilir (hangi motor, kac ms).
#  - HTTP icin Luna'nin kendi `requests` modulu kullanilir (gomulu Python'daki urllib HTTPS desteklemiyor).
import os, threading, time
from collections import deque
import requests
from translator.basetranslator import basetrans
from myutils.config import translatorsetting

KAYNAK_DIL = "en"
HEDEF_DIL = "tr"
HEDEF_DIL_ADI = "Turkish"  # Gemini'ye "yalnizca bu dilde yaz" kurali icin
GEMINI_BEKLE = 1.0  # oyunda Gemini cogunlukla 0,7-1,1 sn; Google ~0,4 sn
GOOGLE_ZAMAN_ASIMI = 5.0
BEKLEME_SN = 30
BAGLAM_SAYISI = 3
ONBELLEK_BOYUT = 2000  # saklanan en fazla ceviri (Luna kapaninca silinir)
# Luna'daki komuta her zaman eklenir. Oyunda gorulen hatalar: "you'd appreciate a call" -> "ararsan memnun olursun"
# (kim kimi ariyor ters), iki satira bolunen cumlenin ilk yarisinin nokta ile bitirilmesi, sen/siz karisikligi.
EK_KURAL = (
    "Address the listener informally (in Turkish always 'sen', never 'siz'). "
    "Keep who does what to whom exactly as in the original (e.g. receiving a call vs. making one). "
    "Game subtitles often split one sentence over two lines: if the input does not end with . ! ? or ..., "
    "translate it as an unfinished fragment that the next line will complete, and do not add a period. "
    "Translate idioms and slang by meaning, never word by word. Examples: "
    "'You got this' = 'Halledersin'; 'You got it' = 'Tamamdır'; 'bring home the bread' = 'parayı kap gel'; "
    "'you'd appreciate a call' = 'aranmaktan memnun olursun'; 'Cut out the painting' = 'Tabloyu çerçevesinden kesip çıkar'; "
    "'Leave the vault' = 'Kasa odasından çık'; 'This is it!' = 'İşte bu!'."
)
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "altyazi_ceviri.log")


def _gunluk(motor, ms, kaynak, sonuc):
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 512 * 1024:
            os.replace(LOG, LOG + ".1")
        with open(LOG, "a", encoding="utf-8") as f:
            # Tarihli zaman: video kaydiyla (xbox-auto-youtube) eslesmesi icin
            f.write("%s\t%s\t%dms\t%s\t=> %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), motor, ms, kaynak, sonuc))
    except Exception:
        pass


def _latin_mi(metin):
    """Lite model arada baska dilde kelime karistiriyor (or. Korece). Latin disi harf varsa reddet.
    Hedef dil Latin alfabesi kullanmiyorsa (Rusca, Arapca...) bu kontrolu kaldirin."""
    for ch in metin:
        if ch.isalpha() and ord(ch) > 0x024F:  # Latin Extended-B sonrasi: Kiril, CJK, Hangul...
            return False
    return True


class _HTTPHata(Exception):
    def __init__(self, kod):
        super().__init__("HTTP %d" % kod)
        self.kod = kod


class _Is(threading.Thread):
    """Arka planda tek bir ceviri istegi; sonuc ya da hata saklanir."""

    def __init__(self, fonk, metin):
        super().__init__(daemon=True)
        self.fonk, self.metin = fonk, metin
        self.sonuc, self.hata = None, None
        self.start()

    def run(self):
        try:
            self.sonuc = self.fonk(self.metin)
        except Exception as e:
            self.hata = e


def _anahtar(metin):
    return " ".join(metin.lower().split())


class TS(basetrans):
    def init(self):
        self.baglam = deque(maxlen=BAGLAM_SAYISI)
        self.gemini_kapali_bitis = 0.0
        # Gorev cumleleri ("Go to the computer.") defalarca tekrar ediyor: Gemini cevirisi saklanir,
        # tekrarinda aninda ve hep ayni ceviri gelir. Gemini gec kalip Google kullanilsa bile Gemini'nin
        # gec gelen cevabi da saklanir; ayni satir bir daha gelirse Google'in hatali/"siz"li cevirisi yerine o gider.
        self.onbellek = {}
        self.kilit = threading.Lock()

    def _sakla(self, metin, ceviri):
        with self.kilit:
            self.onbellek[_anahtar(metin)] = ceviri
            while len(self.onbellek) > ONBELLEK_BOYUT:
                self.onbellek.pop(next(iter(self.onbellek)))

    def _gec_gemini_sakla(self, gemini, metin):
        def bekle():
            gemini.join(15)
            if gemini.sonuc and _latin_mi(gemini.sonuc):
                self._sakla(metin, gemini.sonuc)
        threading.Thread(target=bekle, daemon=True).start()

    def _gemini_ayar(self):
        try:
            a = translatorsetting["chatgpt-3rd-party"]["args"]
            anahtar = a.get("SECRET_KEY", "").split("|")[0].strip()
            return (anahtar, a.get("model") or "gemini-flash-lite-latest", a.get("自定义promt", "")) if anahtar else None
        except Exception:
            return None

    def _gemini(self, metin):
        anahtar, model, komut = self._gemini_ayar()
        icerik = []
        for kaynak, ceviri in list(self.baglam):
            icerik.append({"role": "user", "parts": [{"text": kaynak}]})
            icerik.append({"role": "model", "parts": [{"text": ceviri}]})
        icerik.append({"role": "user", "parts": [{"text": metin}]})
        govde = {"contents": icerik, "generationConfig": {"temperature": 0.2}}
        komut = (komut + " " if komut else "") + EK_KURAL + " " + (
            "Write only in %s; never use words from any other language." % HEDEF_DIL_ADI)
        govde["systemInstruction"] = {"parts": [{"text": komut}]}
        r = requests.request(
            "POST",
            "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model,
            json=govde,
            headers={"x-goog-api-key": anahtar},
            timeout=15,
        )
        if r.status_code == 429:
            self.gemini_kapali_bitis = time.time() + BEKLEME_SN
        if r.status_code != 200:
            raise _HTTPHata(r.status_code)
        cevap = r.json()
        return "".join(p.get("text", "") for p in cevap["candidates"][0]["content"]["parts"]).strip()

    def _google(self, metin):
        r = requests.request(
            "GET",
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": KAYNAK_DIL, "tl": HEDEF_DIL, "dt": "t", "q": metin},
            timeout=GOOGLE_ZAMAN_ASIMI,
        )
        if r.status_code != 200:
            raise _HTTPHata(r.status_code)
        metin = "".join(parca[0] for parca in r.json()[0] if parca and parca[0])
        return metin.replace("​", "").strip()  # Google arada gorunmez bosluk ekliyor ("Prix​​Luxury")

    def translate(self, content):
        metin = str(content).strip()
        if not metin:
            return ""
        t0 = time.time()
        with self.kilit:
            hazir = self.onbellek.get(_anahtar(metin))
        if hazir:
            self.baglam.append((metin, hazir))
            _gunluk("onbellek", (time.time() - t0) * 1000, metin, hazir)
            return hazir
        gemini_var = self._gemini_ayar() is not None
        gemini = _Is(self._gemini, metin) if gemini_var and time.time() >= self.gemini_kapali_bitis else None
        google = _Is(self._google, metin)

        if gemini:
            gemini.join(GEMINI_BEKLE)
            if gemini.sonuc and _latin_mi(gemini.sonuc):
                self.baglam.append((metin, gemini.sonuc))
                self._sakla(metin, gemini.sonuc)
                _gunluk("gemini", (time.time() - t0) * 1000, metin, gemini.sonuc)
                return gemini.sonuc
            if gemini.sonuc:
                neden = "yabanci harf: " + gemini.sonuc
                gemini = None  # bu sonucu asagida da kullanma
            elif gemini.hata is None and gemini.is_alive():
                neden = "gecikti"
                self._gec_gemini_sakla(gemini, metin)
            elif isinstance(gemini.hata, _HTTPHata):
                neden = "HTTP %d" % gemini.hata.kod
            else:
                neden = type(gemini.hata).__name__ if gemini.hata else "bos cevap"
        else:
            neden = "429 beklemesi" if gemini_var else "gemini anahtari yok"

        google.join(GOOGLE_ZAMAN_ASIMI)
        if google.sonuc:
            self.baglam.append((metin, google.sonuc))
            _gunluk("google(%s)" % neden, (time.time() - t0) * 1000, metin, google.sonuc)
            return google.sonuc
        # Google da olmadiysa Gemini'ye biraz daha sans ver
        if gemini:
            gemini.join(3.0)
            if gemini.sonuc and _latin_mi(gemini.sonuc):
                self.baglam.append((metin, gemini.sonuc))
                _gunluk("gemini(gec)", (time.time() - t0) * 1000, metin, gemini.sonuc)
                return gemini.sonuc
        _gunluk("HATA", (time.time() - t0) * 1000, metin, repr(google.hata))
        raise google.hata or Exception("ceviri alinamadi")
