"""Bilgisayarın ses çıkışını (karşı taraf) ve isteğe bağlı olarak mikrofonu (ben)
2 dakikalık WAV parçaları hâlinde kaydeder.

Durdurmak için kayıt klasörüne DUR adlı bir dosya koymak (veya `toplanti durdur`) yeterli.
"""
import argparse
import glob
import os
import threading
import time
import wave

import numpy as np
import soundcard as sc

from .ortak import RATE

BLOK = RATE // 2       # 0,5 sn'lik okuma
SESSIZLIK = 0.003      # tepe seviyesi bunun altındaysa parça sessiz sayılır ve kaydedilmez


class Kaydedici:
    def __init__(self, klasor, parca_sn=120):
        self.klasor = klasor
        self.parca_sn = parca_sn
        self.dur_dosyasi = os.path.join(klasor, "DUR")
        os.makedirs(klasor, exist_ok=True)
        bas = os.path.join(klasor, "baslangic.txt")
        if os.path.exists(bas):  # aynı klasörde devam: zaman ekseni korunur
            with open(bas) as f:
                self.t0 = float(f.read())
        else:
            self.t0 = time.time()
            with open(bas, "w") as f:
                f.write(str(self.t0))
        # Birden fazla cihaz aynı anda kaydedebildiği için sıra numarası ortak ve kilitli
        self._kilit = threading.Lock()
        self._sira = {}

    def _sonraki_sira(self, kim):
        with self._kilit:
            if kim not in self._sira:
                self._sira[kim] = len(glob.glob(os.path.join(self.klasor, f"{kim}_*.wav")))
            n = self._sira[kim]
            self._sira[kim] += 1
            return n

    def _yaz(self, kim, baslangic, veri):
        veri = np.clip(veri, -1, 1)
        pcm = (veri * 32767).astype(np.int16)
        yol = os.path.join(self.klasor, f"{kim}_{self._sonraki_sira(kim):04d}_{baslangic - self.t0:.1f}.wav")
        gecici = yol + ".tmp"
        with wave.open(gecici, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
        os.replace(gecici, yol)  # yazıya dökücü yarım dosya görmesin

    def _durum(self, kim, durum, cihaz):
        with open(os.path.join(self.klasor, f"durum_{kim}.txt"), "w", encoding="utf-8") as f:
            f.write(f"{time.time()}|{durum}|{cihaz}")
        print(f"[{kim}] {time.strftime('%H:%M')} {durum} ({cihaz})", flush=True)

    def kaydet(self, kim, cihaz_al):
        """cihaz_al() -> (ad, kayıt cihazı). Ad değişirse (örn. kulaklık takılınca) yeni cihaza geçer."""
        tampon, parca_bas = [], time.time()
        while not os.path.exists(self.dur_dosyasi):
            try:
                ad, cihaz = cihaz_al()
                print(f"[{kim}] cihaz: {ad}", flush=True)
                son_kontrol = time.time()
                with cihaz.recorder(samplerate=RATE, channels=1, blocksize=1024) as kayit:
                    while not os.path.exists(self.dur_dosyasi):
                        d = kayit.record(numframes=BLOK)
                        tampon.append(d[:, 0] if d.ndim > 1 else d)
                        if time.time() - parca_bas >= self.parca_sn:
                            veri = np.concatenate(tampon)
                            sessiz = float(np.abs(veri).max()) < SESSIZLIK
                            if not sessiz:
                                self._yaz(kim, parca_bas, veri)
                            self._durum(kim, "sessiz" if sessiz else "ses", ad)
                            tampon, parca_bas = [], time.time()
                        if time.time() - son_kontrol >= 3:
                            son_kontrol = time.time()
                            if cihaz_al()[0] != ad:
                                print(f"[{kim}] cihaz değişti", flush=True)
                                break
            except Exception as e:  # cihaz çıkarılırsa vb. kısa bekleyip yeniden dene
                print(f"[{kim}] hata: {e!r}, yeniden deneniyor", flush=True)
                time.sleep(1)
        if tampon:
            veri = np.concatenate(tampon)
            if float(np.abs(veri).max()) >= SESSIZLIK:
                self._yaz(kim, parca_bas, veri)
        print(f"[{kim}] durdu", flush=True)


def _varsayilan_cikis():
    spk = sc.default_speaker()
    return spk.name, sc.get_microphone(id=str(spk.name), include_loopback=True)


def _sabit_cikis(ad):
    return lambda: (ad, sc.get_microphone(id=str(ad), include_loopback=True))


def _ada_gore_cikis(parca):
    def al():
        spk = next((s for s in sc.all_speakers() if parca.lower() in s.name.lower()), sc.default_speaker())
        return spk.name, sc.get_microphone(id=str(spk.name), include_loopback=True)
    return al


def _mikrofon():
    m = sc.default_microphone()
    return m.name, m


def calistir(klasor, cihaz="hepsi", mikrofon=False, parca_sn=120):
    """cihaz: 'hepsi' (tüm çıkışlar), 'varsayilan' ya da çıkış adının bir parçası."""
    k = Kaydedici(klasor, parca_sn)
    if cihaz == "hepsi":
        # Hangi çıkışın kullanıldığını tahmin etmek yerine hepsini dinle; sessiz olanlar kaydedilmez
        hedefler = [_sabit_cikis(s.name) for s in sc.all_speakers()]
    elif cihaz == "varsayilan":
        hedefler = [_varsayilan_cikis]
    else:
        hedefler = [_ada_gore_cikis(cihaz)]
    is_parcaciklari = [threading.Thread(target=k.kaydet, args=("karsi", h)) for h in hedefler]
    if mikrofon:
        is_parcaciklari.append(threading.Thread(target=k.kaydet, args=("ben", _mikrofon)))
    else:
        print("Mikrofon kaydı kapalı", flush=True)
    for t in is_parcaciklari:
        t.start()
    try:
        for t in is_parcaciklari:
            t.join()
    except KeyboardInterrupt:
        open(k.dur_dosyasi, "w").close()
        for t in is_parcaciklari:
            t.join()
    with open(os.path.join(klasor, "KAYIT_BITTI"), "w") as f:
        f.write("ok")
    print("Kayıt bitti.", flush=True)


def main():
    p = argparse.ArgumentParser(description="Ses çıkışını parça parça kaydeder.")
    p.add_argument("klasor")
    p.add_argument("--cihaz", default="hepsi", help="'hepsi', 'varsayilan' ya da çıkış adının bir parçası")
    p.add_argument("--mikrofon", action="store_true", help="Mikrofonu da ayrı kaydet")
    p.add_argument("--parca-sn", type=int, default=120)
    a = p.parse_args()
    calistir(a.klasor, a.cihaz, a.mikrofon, a.parca_sn)


if __name__ == "__main__":
    main()
