"""Motorun yayini (WebSocket :2333). TV uygulamasi ve OBS katmani buraya baglanir; Luna arka planda 2335'te
OCR + ceviri servisi olarak kalir.

  /api/ws/olay        JSON olaylar (yeni istemciler):
                      {"tur": "goster", "bolge": "alt"|"ipucu", "kutu": [x, y, gen, yuk], "tr": "...", "en": "..."}
                      {"tur": "gizle", "bolge": "..."}
                      kutu: Ingilizce yazinin ekrandaki yeri, ekranin 0-1 orani (TV ve OBS kendi boyutuna cevirir).
                      Yeni baglanan istemci ekranda olan son kutulari hemen alir.
  /api/ws/text/trans  Eski bicim (Luna ile ayni): yalniz alt altyazinin Turkcesi, duz metin. Guncellenmemis
                      TV uygulamasi bununla calismaya devam eder.
  GET /api/textinput?text=...   deneme: metin alt bolgede okunmus gibi islenir.
"""
import asyncio
import json
import threading
from urllib.parse import parse_qs, urlsplit

from websockets.asyncio.server import serve

OLAY, ESKI = "/api/ws/olay", "/api/ws/text/trans"


class Yayinci:
    def __init__(self, port=2333, girdi=None):
        self.port, self.girdi = port, girdi
        self.istemciler = {OLAY: set(), ESKI: set()}
        self.son = {}  # bolge -> ekrandaki son "goster" olayi
        self.loop = asyncio.new_event_loop()
        self.hazir = threading.Event()
        threading.Thread(target=self._calis, daemon=True).start()
        self.hazir.wait(5)

    def _calis(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._sunucu())

    async def _sunucu(self):
        async with serve(self._baglanti, "0.0.0.0", self.port, process_request=self._http, ping_interval=20):
            self.hazir.set()
            await asyncio.Future()

    def _http(self, baglanti, istek):
        yol = urlsplit(istek.path)
        if yol.path == "/api/merhaba":
            # TV uygulamasi PC'nin IP'si degisince agi tarayip motoru bununla bulur (WebSocket denemeleri
            # tarayicida kisiliyor, duz HTTP istegi kisilmiyor). Baska kaynaktan (TV uygulamasi) okunabilsin.
            yanit = baglanti.respond(200, "altyazi-motoru\n")
            yanit.headers["Access-Control-Allow-Origin"] = "*"
            return yanit
        if yol.path == "/api/textinput":
            metin = parse_qs(yol.query).get("text", [""])[0]
            if metin and self.girdi:
                self.girdi(metin)
            return baglanti.respond(200, "ok\n")
        if yol.path not in self.istemciler:
            return baglanti.respond(404, "yok\n")
        return None  # WebSocket el sikismasi devam etsin

    async def _baglanti(self, ws):
        yol = urlsplit(ws.request.path).path
        self.istemciler[yol].add(ws)
        try:
            if yol == OLAY:
                for olay in list(self.son.values()):
                    await ws.send(json.dumps(olay, ensure_ascii=False))
            await ws.wait_closed()
        finally:
            self.istemciler[yol].discard(ws)

    def gonder(self, olay):
        """Her is parcacigindan cagrilabilir."""
        self.loop.call_soon_threadsafe(self._dagit, olay)

    def istemci_sayisi(self):
        return {yol: len(k) for yol, k in self.istemciler.items()}

    def _dagit(self, olay):
        if olay["tur"] == "goster":
            self.son[olay["bolge"]] = olay
        else:
            self.son.pop(olay["bolge"], None)
        veri = json.dumps(olay, ensure_ascii=False)
        for ws in list(self.istemciler[OLAY]):
            asyncio.ensure_future(self._yolla(ws, veri))
        if olay["tur"] == "goster" and olay["bolge"] == "alt" and olay.get("tr"):
            for ws in list(self.istemciler[ESKI]):
                asyncio.ensure_future(self._yolla(ws, olay["tr"]))

    @staticmethod
    async def _yolla(ws, veri):
        try:
            await ws.send(veri)
        except Exception:
            pass
