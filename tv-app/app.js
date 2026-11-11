/* Altyazi TV
 * - HDMI goruntusunu (Xbox) tam ekran, uygulamanin ARKASINDA gosterir (tizen.tvwindow)
 * - PC'deki LunaTranslator'in ag servisine baglanir: ws://PC_IP:PORT/api/ws/text/trans
 * - Gelen Turkce ceviriyi ekranin altinda altyazi olarak gosterir
 */
(function () {
  'use strict';

  // ---------- Ayarlar (TV'de kalici saklanir) ----------
  var ayar = {
    // LunaTranslator'in calistigi PC'nin IP'si. Ilk acilista bos: ayar ekrani acilir (KIRMIZI).
    ip: localStorage.getItem('ip') || '',
    port: parseInt(localStorage.getItem('port') || '2333', 10),
    hdmiSira: parseInt(localStorage.getItem('hdmiSira') || '0', 10),
    // v2 anahtarlari: eski kayitli degerler (70px / 46px) yeni tasarimi ezmesin.
    // 150px: GTA'nin Ingilizce altyazisinin (iki satira kadar) hemen ustu.
    altKonum: parseInt(localStorage.getItem('altKonum2') || '150', 10),
    yaziBoyutu: parseInt(localStorage.getItem('yaziBoyutu2') || '40', 10),
    altyaziAcik: localStorage.getItem('altyaziAcik') !== '0'
  };
  function kaydet() {
    try {
      localStorage.setItem('ip', ayar.ip);
      localStorage.setItem('port', String(ayar.port));
      localStorage.setItem('hdmiSira', String(ayar.hdmiSira));
      localStorage.setItem('altKonum2', String(ayar.altKonum));
      localStorage.setItem('yaziBoyutu2', String(ayar.yaziBoyutu));
      localStorage.setItem('altyaziAcik', ayar.altyaziAcik ? '1' : '0');
    } catch (e) { /* depolama yoksa sorun degil */ }
  }

  var $ = function (id) { return document.getElementById(id); };
  var elAltyazi = $('altyazi'), elDurum = $('durum');
  var elAyarlar = $('ayarlar'), elIp = $('ipKutusu'), elPort = $('portYazi'), elYardim = $('yardim');

  // ---------- Durum mesaji ----------
  var durumZaman = null;
  function durum(mesaj, kalici) {
    elDurum.textContent = mesaj;
    elDurum.style.opacity = '1';
    clearTimeout(durumZaman);
    if (!kalici) durumZaman = setTimeout(function () { elDurum.style.opacity = '0'; }, 4000);
  }

  // ---------- Altyazi gorunumu ----------
  function stilUygula() {
    elAltyazi.style.bottom = ayar.altKonum + 'px';
    elAltyazi.style.fontSize = ayar.yaziBoyutu + 'px';
  }
  // Yalnizca son ceviri gorunur; yenisi gelince eskisi solup kaybolur.
  // 2 yapilirsa bir onceki ceviri ustte soluk olarak kalir.
  // Her satir kendi suresi dolunca da solup kaybolur.
  var EN_FAZLA_SATIR = 1;
  function satirKaldir(el) {
    if (!el.parentNode) return;
    el.classList.add('sonuyor');
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 650);
  }
  function altyaziGoster(metin) {
    if (!ayar.altyaziAcik) return;
    metin = String(metin || '').trim();
    if (!metin) return;
    var eskiler = elAltyazi.querySelectorAll('.satir:not(.sonuyor)');
    // Ayni metin zaten en altta duruyorsa (SARI/YUKARI/ASAGI onizlemesi) tekrar ekleme
    if (eskiler.length && eskiler[eskiler.length - 1].textContent === metin) return;
    for (var i = 0; i < eskiler.length; i++) {
      eskiler[i].classList.add('eski');
      if (i <= eskiler.length - EN_FAZLA_SATIR) satirKaldir(eskiler[i]);
    }
    var el = document.createElement('div');
    el.className = 'satir';
    el.textContent = metin;
    elAltyazi.appendChild(el);
    // Altyazi uzunluguna gore ekranda kalma suresi (4-10 sn)
    var sure = Math.min(10000, Math.max(4000, metin.length * 90));
    setTimeout(function () { satirKaldir(el); }, sure);
  }
  function altyaziTemizle() {
    var hepsi = elAltyazi.querySelectorAll('.satir');
    for (var i = 0; i < hepsi.length; i++) satirKaldir(hepsi[i]);
  }

  // ---------- HDMI goruntusu (tvwindow) ----------
  var hdmiListesi = [];
  function hdmiBaslat() {
    if (!window.tizen || !tizen.tvwindow) { durum('tvwindow API yok (TV disinda mi calisiyor?)'); return; }
    try {
      tizen.tvwindow.show(
        function () { hdmiKaynagiSec(); },
        function (e) { durum('Goruntu acilamadi: ' + e.message, true); },
        ['0px', '0px', '1920px', '1080px'],
        'MAIN',
        'BEHIND'
      );
    } catch (e) {
      durum('tvwindow hatasi: ' + e.message, true);
    }
  }
  function hdmiKaynagiSec() {
    tizen.systeminfo.getPropertyValue('VIDEOSOURCE', function (vs) {
      hdmiListesi = (vs.connected || []).filter(function (s) { return s.type === 'HDMI'; });
      if (!hdmiListesi.length) { durum('Bagli HDMI cihazi bulunamadi', true); return; }
      if (ayar.hdmiSira >= hdmiListesi.length) ayar.hdmiSira = 0;
      var kaynak = hdmiListesi[ayar.hdmiSira];
      tizen.tvwindow.setSource(kaynak,
        function () { durum('HDMI ' + kaynak.number + ' gosteriliyor'); },
        function (e) { durum('HDMI secilemedi: ' + e.message, true); },
        'MAIN');
    }, function (e) { durum('Kaynak listesi alinamadi: ' + e.message, true); });
  }
  function sonrakiHdmi() {
    if (!hdmiListesi.length) { hdmiKaynagiSec(); return; }
    ayar.hdmiSira = (ayar.hdmiSira + 1) % hdmiListesi.length;
    kaydet();
    hdmiKaynagiSec();
  }

  // ---------- LunaTranslator baglantisi ----------
  var ws = null, yenidenZaman = null, bekleme = 1000, sonMetin = '';
  function mesajdanMetin(veri) {
    // Format garanti degil: duz metin ya da JSON olabilir
    if (typeof veri !== 'string') return '';
    var t = veri.trim();
    if (t.charAt(0) === '{' || t.charAt(0) === '[') {
      try {
        var j = JSON.parse(t);
        if (Array.isArray(j)) j = j[j.length - 1];
        if (j && typeof j === 'object') {
          return j.result || j.text || j.trans || j.translation || j.content || '';
        }
      } catch (e) { /* duz metin gibi davran */ }
    }
    return t;
  }
  function baglan() {
    clearTimeout(yenidenZaman);
    if (ws) { try { ws.onclose = null; ws.close(); } catch (e) {} ws = null; }
    if (!ayar.ip) { durum('PC IP adresi girilmedi - KIRMIZI tusa bas', true); return; }
    var url = 'ws://' + ayar.ip + ':' + ayar.port + '/api/ws/text/trans';
    durum('Baglaniyor: ' + ayar.ip + ':' + ayar.port, true);
    try { ws = new WebSocket(url); } catch (e) { yenidenDene(); return; }
    ws.onopen = function () { bekleme = 1000; durum('PC\'ye baglandi ✓'); };
    ws.onmessage = function (ev) {
      var m = mesajdanMetin(ev.data);
      if (m && m !== sonMetin) { sonMetin = m; altyaziGoster(m); }
    };
    ws.onerror = function () { /* onclose ele alir */ };
    ws.onclose = function () { durum('Baglanti yok, tekrar deneniyor...', true); yenidenDene(); };
  }
  function yenidenDene() {
    clearTimeout(yenidenZaman);
    yenidenZaman = setTimeout(baglan, bekleme);
    bekleme = Math.min(bekleme * 2, 15000);
  }

  // ---------- Ayar ekrani (kumanda ile IP girisi) ----------
  var ayarAcik = false, ipTaslak = '';
  function ayarCiz() {
    elIp.textContent = ipTaslak + '_';
    elPort.textContent = String(ayar.port);
  }
  function ayarAc() {
    ayarAcik = true; ipTaslak = ayar.ip;
    elAyarlar.classList.remove('gizli'); ayarCiz();
  }
  function ayarKapat(kaydetsinMi) {
    ayarAcik = false; elAyarlar.classList.add('gizli');
    if (kaydetsinMi) { ayar.ip = ipTaslak; kaydet(); baglan(); }
  }
  function ayarTus(kod) {
    if (kod >= 48 && kod <= 57) { if (ipTaslak.length < 15) ipTaslak += String(kod - 48); }
    else if (kod === 13) { if (ipTaslak && ipTaslak.slice(-1) !== '.' && ipTaslak.split('.').length < 4) ipTaslak += '.'; }
    else if (kod === 10009 || kod === 8) { ipTaslak = ipTaslak.slice(0, -1); }
    else if (kod === 38) { ayar.port = Math.min(65535, ayar.port + 1); }
    else if (kod === 40) { ayar.port = Math.max(1, ayar.port - 1); }
    else if (kod === 403) { ayarKapat(true); return; }
    ayarCiz();
  }

  // ---------- Kumanda ----------
  var KAYITLI_TUSLAR = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'ColorF0Red', 'ColorF1Green', 'ColorF2Yellow', 'ColorF3Blue'];
  function tuslariKaydet() {
    if (!window.tizen || !tizen.tvinputdevice) return;
    KAYITLI_TUSLAR.forEach(function (k) { try { tizen.tvinputdevice.registerKey(k); } catch (e) {} });
  }
  var yardimZaman = null;
  function yardimGoster() {
    elYardim.classList.remove('gizli');
    clearTimeout(yardimZaman);
    yardimZaman = setTimeout(function () { elYardim.classList.add('gizli'); }, 6000);
  }

  document.addEventListener('keydown', function (e) {
    var kod = e.keyCode;
    if (ayarAcik) { e.preventDefault(); ayarTus(kod); return; }
    switch (kod) {
      case 403: ayarAc(); break;                                   // KIRMIZI
      case 404:                                                    // YESIL
        ayar.altyaziAcik = !ayar.altyaziAcik; kaydet();
        if (!ayar.altyaziAcik) altyaziTemizle();
        durum('Altyazi ' + (ayar.altyaziAcik ? 'acik' : 'kapali'));
        break;
      case 405:                                                    // SARI
        ayar.yaziBoyutu = ayar.yaziBoyutu >= 56 ? 32 : ayar.yaziBoyutu + 4;
        kaydet(); stilUygula(); altyaziGoster(sonMetin || 'Örnek altyazı boyutu: şğıİçöü');
        break;
      case 406: sonrakiHdmi(); break;                              // MAVI
      case 38: ayar.altKonum = Math.min(900, ayar.altKonum + 15); kaydet(); stilUygula(); altyaziGoster(sonMetin || 'Altyazı konumu'); break;
      case 40: ayar.altKonum = Math.max(10, ayar.altKonum - 15); kaydet(); stilUygula(); altyaziGoster(sonMetin || 'Altyazı konumu'); break;
      case 13: yardimGoster(); break;                              // OK
      case 10009:                                                  // GERI = cikis
        try { tizen.tvwindow.hide(function () {}, function () {}, 'MAIN'); } catch (x) {}
        try { tizen.application.getCurrentApplication().exit(); } catch (x) {}
        break;
      default: return;
    }
    e.preventDefault();
  });

  // ---------- Basla ----------
  window.addEventListener('load', function () {
    stilUygula();
    tuslariKaydet();
    hdmiBaslat();
    yardimGoster();
    if (ayar.ip) baglan(); else ayarAc();
  });
})();
