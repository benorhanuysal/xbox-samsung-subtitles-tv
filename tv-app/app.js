/* Altyazi TV
 * - HDMI goruntusunu (Xbox) tam ekran, uygulamanin ARKASINDA gosterir (tizen.tvwindow)
 * - PC'deki altyazi motoruna baglanir: ws://PC_IP:PORT/api/ws/olay
 *   {"tur":"goster","bolge":"alt"|"ipucu","kutu":[x,y,gen,yuk] (ekranin 0-1 orani),"tr":"..."} / {"tur":"gizle",...}
 *   Her Turkce metin Ingilizcenin TAM USTUNE siyah zeminle yazilir (Ingilizceyi ortur): alttaki altyazi da,
 *   sol ustteki gorev/ipucu kutusu da.
 * - Motor yoksa (yalniz LunaTranslator) eski adrese duser: /api/ws/text/trans, Turkce ekranin altinda
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
    for (var b in kapaklar) kapaklar[b].el.classList.add('gizli');
  }

  // ---------- Kapak gorunumu (motor): Turkce, Ingilizcenin tam ustunde ----------
  var W = 1920, H = 1080, PAY = 14;
  var kapaklar = {};  // bolge -> {el, zamanlayici, gosterildi, metin}
  function okumaSuresi(metin) { return Math.min(6000, 2000 + metin.length * 60); }
  function kapakAl(bolge) {
    if (!kapaklar[bolge]) {
      var el = document.createElement('div');
      el.className = 'kapak gizli ' + bolge;
      document.body.appendChild(el);
      kapaklar[bolge] = { el: el, zamanlayici: null, gosterildi: 0, metin: '' };
    }
    return kapaklar[bolge];
  }
  function sigdir(el, enBuyuk, enKucuk, azamiYukseklik) {
    // Turkce Ingilizceden uzun olabilir: kutuya sigana kadar kucult
    for (var b = enBuyuk; b >= enKucuk; b--) {
      el.style.fontSize = b + 'px';
      if (el.scrollHeight <= azamiYukseklik && el.scrollWidth <= el.clientWidth + 1) return;
    }
  }
  function kapakGoster(o) {
    if (!ayar.altyaziAcik) return;
    var k = kapakAl(o.bolge);
    clearTimeout(k.zamanlayici);
    var x = o.kutu[0] * W, y = o.kutu[1] * H, g = o.kutu[2] * W, h = o.kutu[3] * H;
    var el = k.el;
    el.textContent = o.tr;
    el.style.left = Math.max(0, x - PAY) + 'px';
    el.style.width = (g + 2 * PAY) + 'px';
    el.style.height = 'auto';
    el.style.minHeight = (h + 2 * PAY) + 'px';
    // Satir yuksekligi Ingilizce yazidan tahmin; SARI tusla (yaziBoyutu, varsayilan 40) buyutulup kucultulur
    var satir = Math.max(1, Math.round(h / (o.bolge === 'ipucu' ? 29 : 34)));
    var boyut = Math.round(Math.max(18, Math.min(40, h / satir * 0.8)) * ayar.yaziBoyutu / 40);
    sigdir(el, boyut, 16, (h + 2 * PAY) * (o.bolge === 'ipucu' ? 2.2 : 1.9));
    var yuk = el.offsetHeight;
    // alt: alt kenar sabit, yukari buyur; ipucu: ust kenar sabit, asagi buyur
    el.style.top = Math.max(0, o.bolge === 'alt' ? y + h + PAY - yuk : y - PAY) + 'px';
    el.classList.remove('gizli');
    k.gosterildi = Date.now();
    k.metin = o.tr;
  }
  function kapakGizle(o) {
    var k = kapaklar[o.bolge];
    if (!k) return;
    clearTimeout(k.zamanlayici);
    // Altyazi Ingilizcesi gitse de Turkcesi okuma suresi dolana kadar kalir; ipucu kutusu gidince hemen
    var kalan = o.bolge === 'alt' ? Math.max(0, k.gosterildi + okumaSuresi(k.metin) - Date.now()) : 0;
    k.zamanlayici = setTimeout(function () { k.el.classList.add('gizli'); }, kalan);
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
  // Once motorun konumlu adresi; iki kez acilamazsa (yalniz LunaTranslator calisiyor) eski adrese duser,
  // sonra yeniden motoru dener.
  var kip = 'olay', basarisiz = 0;
  function olayIsle(veri) {
    var o;
    try { o = JSON.parse(veri); } catch (e) { return; }
    if (o.tur === 'goster' && o.kutu && o.tr) { sonMetin = o.tr; kapakGoster(o); }
    else if (o.tur === 'gizle') kapakGizle(o);
  }
  function baglan() {
    clearTimeout(yenidenZaman);
    if (aramada) return;  // PC aramasi bitince kendisi baglanir
    if (ws) { try { ws.onclose = null; ws.close(); } catch (e) {} ws = null; }
    if (!ayar.ip) { durum('PC IP adresi girilmedi - KIRMIZI tusa bas', true); return; }
    var yol = kip === 'olay' ? '/api/ws/olay' : '/api/ws/text/trans';
    var url = 'ws://' + ayar.ip + ':' + ayar.port + yol;
    var acildi = false, soket;
    durum('Baglaniyor: ' + ayar.ip + ':' + ayar.port, true);
    try { soket = ws = new WebSocket(url); } catch (e) { yenidenDene(); return; }
    // Kimsenin olmadigi IP'ye baglanma denemesi tarayicida 20 sn'den uzun asili kalabiliyor.
    // Yalniz BU denemeyi kapat (global ws o sirada yeni bir deneme olabilir).
    var acilisSiniri = setTimeout(function () { if (!acildi) { try { soket.close(); } catch (e) {} } }, 4000);
    soket.onopen = function () {
      clearTimeout(acilisSiniri);
      acildi = true; bekleme = 1000; basarisiz = 0;
      durum(kip === 'olay' ? 'Altyazi motoruna baglandi ✓' : 'PC\'ye baglandi ✓ (eski bicim)');
    };
    soket.onmessage = function (ev) {
      if (kip === 'olay') { olayIsle(ev.data); return; }
      var m = mesajdanMetin(ev.data);
      if (m && m !== sonMetin) { sonMetin = m; altyaziGoster(m); }
    };
    soket.onerror = function () { /* onclose ele alir */ };
    soket.onclose = function () {
      clearTimeout(acilisSiniri);
      if (soket !== ws) return;  // eski bir denemenin gec gelen kapanisi
      if (!acildi && ++basarisiz >= 2) {
        if (kip === 'eski') { pcAra(); return; }  // iki adres de olmadi: PC'nin IP'si degismis olabilir
        kip = 'eski'; basarisiz = 0; bekleme = 1000;
      }
      durum('Baglanti yok, tekrar deneniyor...', true);
      yenidenDene();
    };
  }

  // ---------- PC'yi kendiliginden bulma ----------
  // Modem PC'ye her zaman ayni IP'yi vermiyor (or. .104 -> .109); kayitli IP cevap vermezse ayni agdaki
  // adresler denenir, motorun /api/merhaba adresine "altyazi-motoru" diye cevap veren ilk adres kaydedilir.
  // Kumandayla IP girmek gerekmez. WebSocket degil duz HTTP: tarayici basarisiz WebSocket denemelerinden sonra
  // yenilerini bekletiyor (Chromium kisma), 254 adreslik taramada dogru adres bile zaman asimina dusuyordu.
  // Eski IP'nin yakinindan baslanir: modem genelde yakin bir adres verir.
  var aramada = false, sonArama = 0;
  function pcAra() {
    if (aramada) return;
    var parca = (ayar.ip || '').split('.');
    // PC kapaliyken her birkac saniyede 254 adres taranmasin: basarisiz aramadan sonra 1 dk bekle
    if (parca.length !== 4 || Date.now() - sonArama < 60000) { kip = 'olay'; basarisiz = 0; yenidenDene(); return; }
    sonArama = Date.now();
    aramada = true;
    var ag = parca.slice(0, 3).join('.') + '.';
    durum('PC araniyor: ' + ag + '* ...', true);
    var adaylar = [], bulundu = false, i, eski = parseInt(parca[3], 10) || 0;
    for (i = 1; i < 255; i++) adaylar.push(i);
    adaylar.sort(function (a, b) { return Math.abs(a - eski) - Math.abs(b - eski); });
    for (i = 0; i < adaylar.length; i++) adaylar[i] = ag + adaylar[i];
    function dene(ip, bitti) {
      var istek = new XMLHttpRequest(), bitirildi = false;
      function son() { if (!bitirildi) { bitirildi = true; bitti(); } }
      try {
        istek.open('GET', 'http://' + ip + ':' + ayar.port + '/api/merhaba', true);
        istek.timeout = 1500;
        istek.onload = function () {
          if (!bulundu && istek.status === 200 && String(istek.responseText).indexOf('altyazi-motoru') === 0) {
            bulundu = true; aramada = false;
            ayar.ip = ip; kaydet();
            kip = 'olay'; basarisiz = 0; bekleme = 1000;
            durum('PC bulundu: ' + ip, true);
            baglan();
          }
          son();
        };
        istek.onerror = istek.ontimeout = istek.onabort = son;
        istek.send();
      } catch (e) { son(); }
    }
    // TV tarayicisini bogmamak icin 32'lik gruplar
    function grup(bas) {
      if (bulundu) return;
      if (bas >= adaylar.length) { aramada = false; kip = 'olay'; basarisiz = 0; yenidenDene(); return; }
      var kalan = Math.min(32, adaylar.length - bas);
      for (var j = bas; j < bas + 32 && j < adaylar.length; j++) {
        dene(adaylar[j], function () { if (--kalan === 0) grup(bas + 32); });
      }
    }
    grup(0);
  }
  function yenidenDene() {
    clearTimeout(yenidenZaman);
    if (aramada) return;
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
        kaydet(); stilUygula();
        if (kip === 'olay') durum('Yazi boyutu: %' + Math.round(ayar.yaziBoyutu / 40 * 100) + ' (bir sonraki satirda)');
        else altyaziGoster(sonMetin || 'Örnek altyazı boyutu: şğıİçöü');
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
