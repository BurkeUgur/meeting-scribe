"""Kayıt klasöründeki yeni ses parçalarını yazıya döker ve transkripti zaman sırasıyla günceller.

İki mod var:
- ana (varsayılan): tüm parçaları tek bir dilde (örn. İngilizce) hızlı bir modelle döker
  -> transkript.txt
- diger: her parçanın dilini tespit eder; sadece belirtilen dillerdekileri (örn. Arapça,
  Fransızca) çok dilli büyük modelle orijinal dilinde döker -> transkript_diger.txt
  Çeviri kanalı gelmeyip salon sesi geldiğinde işe yarar.

Kayıt bitip tüm parçalar işlenince kendiliğinden kapanır.
"""
import argparse
import glob
import json
import os
import time
import wave

import numpy as np
from faster_whisper import WhisperModel

from .ortak import kayit_bitti_mi, parca_bilgisi, sozluk_oku, sure_bicimi

ETIKET = {"karsi": "KARŞI TARAF", "ben": "BEN"}


class Transkript:
    """segmentler + işlenen dosyalar listesi; kesilip yeniden başlatılınca kaldığı yerden devam eder."""

    def __init__(self, klasor, ek=""):
        self.klasor = klasor
        self.seg_yolu = os.path.join(klasor, f"segmentler{ek}.json")
        self.liste_yolu = os.path.join(klasor, f"islenen{ek}.txt")
        self.metin_yolu = os.path.join(klasor, f"transkript{ek}.txt")
        self.segmentler = []
        if os.path.exists(self.seg_yolu):
            with open(self.seg_yolu, encoding="utf-8") as f:
                self.segmentler = json.load(f)
        self.islenen = set()
        if os.path.exists(self.liste_yolu):
            with open(self.liste_yolu, encoding="utf-8") as f:
                self.islenen = set(f.read().split())

    def yeni_parcalar(self, en_erken=0.0):
        parcalar = []
        for yol in glob.glob(os.path.join(self.klasor, "*.wav")):
            bilgi = parca_bilgisi(yol)
            if bilgi and os.path.basename(yol) not in self.islenen and bilgi[1] >= en_erken:
                parcalar.append((bilgi[1], yol, bilgi[0]))
        return [(yol, kim, bas) for bas, yol, kim in sorted(parcalar)]

    def ekle(self, dosya, kim, bas, sonuc, dil=None):
        for s in sonuc:
            metin = s.text.strip()
            if metin:
                kayit = {"dosya": dosya, "kim": kim, "t": bas + s.start, "metin": metin}
                if dil:
                    kayit["dil"] = dil
                self.segmentler.append(kayit)

    def islendi(self, dosya):
        self.islenen.add(dosya)
        with open(self.liste_yolu, "a", encoding="utf-8") as f:
            f.write(dosya + "\n")
        self.kaydet()

    def kaydet(self):
        with open(self.seg_yolu, "w", encoding="utf-8") as f:
            json.dump(self.segmentler, f, ensure_ascii=False)
        satirlar = []
        for s in sorted(self.segmentler, key=lambda s: s["t"]):
            dil = f" ({s['dil']})" if s.get("dil") else ""
            satirlar.append(f"[{sure_bicimi(s['t'])}] {ETIKET.get(s['kim'], s['kim'])}{dil}: {s['metin']}")
        with open(self.metin_yolu, "w", encoding="utf-8") as f:
            f.write("\n".join(satirlar) + "\n")


def ses_oku(yol):
    with wave.open(yol, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def ana(klasor, model="small.en", dil="en", sozluk=None, bekleme=10):
    m = WhisperModel(model, device="cpu", compute_type="int8")
    ipucu = sozluk_oku(sozluk)
    tr = Transkript(klasor)
    while True:
        yeni = tr.yeni_parcalar()
        for yol, kim, bas in yeni:
            sonuc, _ = m.transcribe(ses_oku(yol), language=dil, vad_filter=True, beam_size=5,
                                    initial_prompt=ipucu)
            tr.ekle(os.path.basename(yol), kim, bas, sonuc)
            tr.islendi(os.path.basename(yol))
            print("işlendi:", os.path.basename(yol), flush=True)
        if kayit_bitti_mi(klasor) and not yeni:
            tr.kaydet()
            print("Tüm parçalar işlendi.", flush=True)
            return
        time.sleep(bekleme)


def diger(klasor, diller=("ar", "fr"), model="large-v3", en_erken=0.0, bekleme=10):
    # Küçük model sadece dil tespiti için; aksanlı İngilizce bazen başka dil sanılır,
    # bu yüzden yalnızca istenen diller büyük modele gider.
    tespit = WhisperModel("tiny", device="cpu", compute_type="int8")
    buyuk = WhisperModel(model, device="cpu", compute_type="int8")
    tr = Transkript(klasor, "_diger")
    while True:
        yeni = tr.yeni_parcalar(en_erken)
        for yol, kim, bas in yeni:
            ses = ses_oku(yol)
            _, bilgi = tespit.transcribe(ses, vad_filter=True)
            if bilgi.language in diller and bilgi.language_probability > 0.5:
                sonuc, _ = buyuk.transcribe(ses, language=bilgi.language, vad_filter=True, beam_size=1)
                tr.ekle(os.path.basename(yol), kim, bas, sonuc, dil=bilgi.language)
            tr.islendi(os.path.basename(yol))
            print(f"işlendi (diğer): {os.path.basename(yol)} dil={bilgi.language}", flush=True)
        if kayit_bitti_mi(klasor) and not yeni:
            tr.kaydet()
            print("Tüm parçalar işlendi (diğer).", flush=True)
            return
        time.sleep(bekleme)


def main():
    p = argparse.ArgumentParser(description="Kayıt parçalarını yazıya döker.")
    p.add_argument("klasor")
    p.add_argument("--mod", choices=["ana", "diger"], default="ana")
    p.add_argument("--model", help="Whisper modeli (ana: small.en, diger: large-v3)")
    p.add_argument("--dil", default="en", help="ana mod için konuşma dili")
    p.add_argument("--diller", default="ar,fr", help="diger mod için virgülle ayrılmış diller")
    p.add_argument("--sozluk", help="Doğru yazılması istenen isim/kısaltma listesi (satır başına bir terim)")
    p.add_argument("--en-erken", type=float, default=0.0, help="diger mod: bu saniyeden önceki parçaları atla")
    a = p.parse_args()
    if a.mod == "ana":
        ana(a.klasor, a.model or "small.en", a.dil, a.sozluk)
    else:
        diger(a.klasor, tuple(a.diller.split(",")), a.model or "large-v3", a.en_erken)


if __name__ == "__main__":
    main()
