"""Modüller arasında paylaşılan küçük yardımcılar."""
import os
import re

RATE = 16000  # Whisper'ın beklediği örnekleme hızı

# Ses parçası adları: <kim>_<sıra>_<başlangıç saniyesi>.wav  (örn. karsi_0012_1349.5.wav)
PARCA_DESENI = re.compile(r"^(?P<kim>[a-z]+)_(?P<sira>\d+)_(?P<bas>\d+(?:\.\d+)?)\.wav$")


def parca_bilgisi(yol):
    """Dosya adından (kim, başlangıç saniyesi) döndürür; uymayan dosyalar için None."""
    m = PARCA_DESENI.match(os.path.basename(yol))
    if not m:
        return None
    return m.group("kim"), float(m.group("bas"))


def sure_bicimi(t):
    t = int(t)
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def sozluk_oku(yol):
    """Sözlük dosyasındaki isim ve kısaltmaları tek satırlık bir ipucuna çevirir.
    Her satır bir terim; # ile başlayan satırlar yorumdur."""
    if not yol or not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        terimler = [s.strip() for s in f if s.strip() and not s.lstrip().startswith("#")]
    return ", ".join(terimler) + "." if terimler else None


def kayit_bitti_mi(klasor):
    return os.path.exists(os.path.join(klasor, "KAYIT_BITTI"))
