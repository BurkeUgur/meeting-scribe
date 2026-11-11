"""`toplanti` komutu: kaydı ve yazıya dökmeyi arka planda başlatır, durdurur, durumu gösterir."""
import argparse
import datetime
import glob
import os
import subprocess
import sys
import time

from .ortak import parca_bilgisi


def _klasor(a):
    k = a.klasor or os.path.join("kayitlar", datetime.date.today().isoformat())
    return os.path.abspath(k)


def _arka_planda(klasor, ad, modul, *argumanlar):
    """Modülü ayrı, pencere açmayan bir süreç olarak başlatır; çıktısı <ad>_log.txt'ye gider."""
    ortam = dict(os.environ, PYTHONIOENCODING="utf-8")
    bayraklar = 0
    if os.name == "nt":
        bayraklar = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    log = open(os.path.join(klasor, f"{ad}_log.txt"), "a", encoding="utf-8")
    p = subprocess.Popen([sys.executable, "-u", "-m", f"toplanti_takip.{modul}", klasor, *argumanlar],
                         stdout=log, stderr=subprocess.STDOUT, env=ortam, creationflags=bayraklar,
                         start_new_session=(os.name != "nt"))
    with open(os.path.join(klasor, f"{ad}.pid"), "w") as f:
        f.write(str(p.pid))
    print(f"  {ad}: başladı (pid {p.pid})")


def baslat(a):
    klasor = _klasor(a)
    os.makedirs(klasor, exist_ok=True)
    for dosya in ("DUR", "KAYIT_BITTI"):  # önceki bir durdurmadan kalanlar
        yol = os.path.join(klasor, dosya)
        if os.path.exists(yol):
            os.remove(yol)
    print(f"Kayıt klasörü: {klasor}")
    kayit_arg = ["--cihaz", a.cihaz] + (["--mikrofon"] if a.mikrofon else [])
    _arka_planda(klasor, "kayit", "kaydet", *kayit_arg)
    ana_arg = ["--mod", "ana", "--dil", a.dil] + (["--model", a.model] if a.model else [])
    if a.sozluk:
        ana_arg += ["--sozluk", os.path.abspath(a.sozluk)]
    _arka_planda(klasor, "yazi", "yaziya_dok", *ana_arg)
    if a.diger_diller:
        _arka_planda(klasor, "diger", "yaziya_dok", "--mod", "diger", "--diller", a.diger_diller)
    print("Durdurmak için: toplanti durdur" + (f" --klasor \"{a.klasor}\"" if a.klasor else ""))


def durdur(a):
    klasor = _klasor(a)
    open(os.path.join(klasor, "DUR"), "w").close()
    print("Kayıt durduruluyor...")
    for _ in range(30):
        if os.path.exists(os.path.join(klasor, "KAYIT_BITTI")):
            print("Kayıt durdu. Yazıya dökme kalan parçaları bitirince kendiliğinden kapanacak.")
            return
        time.sleep(1)
    print("Kayıt süreci 30 sn içinde yanıt vermedi; 'toplanti durum' ile kontrol edin.")


def durum(a):
    klasor = _klasor(a)
    if not os.path.isdir(klasor):
        print(f"Klasör yok: {klasor}")
        return
    parcalar = [p for p in glob.glob(os.path.join(klasor, "*.wav")) if parca_bilgisi(p)]
    islenen = 0
    yol = os.path.join(klasor, "islenen.txt")
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as f:
            islenen = len(f.read().split())
    print(f"Klasör: {klasor}")
    print(f"Kayıt: {'bitti' if os.path.exists(os.path.join(klasor, 'KAYIT_BITTI')) else 'sürüyor'}")
    for d in sorted(glob.glob(os.path.join(klasor, "durum_*.txt"))):
        with open(d, encoding="utf-8") as f:
            t, ses, cihaz = f.read().split("|", 2)
        print(f"  son kontrol {time.strftime('%H:%M:%S', time.localtime(float(t)))}: {ses} ({cihaz})")
    print(f"Ses parçası: {len(parcalar)}, yazıya dökülen: {islenen}")
    tr = os.path.join(klasor, "transkript.txt")
    if os.path.exists(tr):
        with open(tr, encoding="utf-8") as f:
            satirlar = f.read().strip().splitlines()[-a.son:]
        print("--- transkriptin sonu ---")
        print("\n".join(satirlar))


def cihazlar(a):
    """Ses çıkışlarını listeler ve birkaç saniye dinleyip hangisinden ses geldiğini gösterir."""
    import numpy as np
    import soundcard as sc
    varsayilan = sc.default_speaker().name
    print(f"{a.sure} sn dinleniyor...")
    for s in sc.all_speakers():
        m = sc.get_microphone(id=str(s.name), include_loopback=True)
        with m.recorder(samplerate=16000, channels=1) as r:
            d = r.record(numframes=16000 * a.sure)
        tepe = float(np.abs(d).max())
        isaret = " (varsayılan)" if s.name == varsayilan else ""
        print(f"  {'SES VAR' if tepe >= 0.003 else 'sessiz ':8} tepe={tepe:.4f}  {s.name}{isaret}")


def main():
    p = argparse.ArgumentParser(prog="toplanti", description="Toplantıyı kaydedip yazıya döker.")
    alt = p.add_subparsers(dest="komut", required=True)

    b = alt.add_parser("baslat", help="Kaydı ve yazıya dökmeyi arka planda başlat")
    b.add_argument("--klasor", help="Kayıt klasörü (varsayılan: kayitlar/<bugünün tarihi>)")
    b.add_argument("--cihaz", default="hepsi", help="'hepsi' (varsayılan), 'varsayilan' ya da çıkış adının parçası")
    b.add_argument("--mikrofon", action="store_true", help="Kendi mikrofonunuzu da ayrı kaydet")
    b.add_argument("--dil", default="en", help="Ana konuşma dili (varsayılan: en)")
    b.add_argument("--model", help="Ana dil için Whisper modeli (varsayılan: small.en)")
    b.add_argument("--sozluk", help="Doğru yazılması istenen isim/kısaltmaların listesi")
    b.add_argument("--diger-diller", default="ar,fr",
                   help="Ayrıca çok dilli modelle dökülecek diller (varsayılan: ar,fr; kapatmak için '')")
    b.set_defaults(f=baslat)

    d = alt.add_parser("durdur", help="Kaydı durdur")
    d.add_argument("--klasor")
    d.set_defaults(f=durdur)

    s = alt.add_parser("durum", help="Kayıt ve yazıya dökme durumunu göster")
    s.add_argument("--klasor")
    s.add_argument("--son", type=int, default=10, help="Gösterilecek son transkript satırı sayısı")
    s.set_defaults(f=durum)

    c = alt.add_parser("cihazlar", help="Ses çıkışlarını listele, hangisinden ses geldiğini ölç")
    c.add_argument("--sure", type=int, default=3)
    c.set_defaults(f=cihazlar)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
