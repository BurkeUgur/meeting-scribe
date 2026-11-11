# toplanti-takip

Online toplantıların (Interactio, Zoom, Teams, Webex vb.) sesini **bilgisayarın ses çıkışından** kaydeder ve yazıya döker. Toplantı uygulamasına bağlanmaz, bot eklemez; hoparlöre ne geliyorsa onu kaydeder. Her şey bilgisayarınızda çalışır, ses hiçbir yere gönderilmez.

- Ses 2 dakikalık parçalar hâlinde kaydedilir. Sessiz parçalar (aralar) kaydedilmez.
- Yazıya dökme kayıtla eş zamanlı ilerler; transkript her parçada güncellenir.
- Tüm ses çıkışları aynı anda dinlenir. Toplantı sırasında kulaklık ya da harici hoparlör değiştirseniz de kayıt kesilmez.
- Çeviri kanalı yerine salon sesi gelirse ve konuşmacı Arapça ya da Fransızca konuşursa, bu kısımlar çok dilli bir modelle orijinal dilinde ayrıca yazıya dökülür.

> Yalnızca Windows'ta denendi. Ses çıkışını kaydetmek için `SoundCard` kütüphanesinin loopback desteği kullanılıyor; macOS'te bu desteklenmiyor.

## Kurulum

Python 3.9 veya üstü gerekir.

```
pip install git+https://github.com/BurkeUgur/toplanti-takip.git
```

Modeller ilk kullanımda otomatik indirilir: ana dil için `small.en` yaklaşık 500 MB, Arapça/Fransızca için `large-v3` yaklaşık 3 GB.

## Kullanım

```
toplanti cihazlar          # ses çıkışlarını listeler, hangisinden ses geldiğini ölçer
toplanti baslat            # kaydı ve yazıya dökmeyi arka planda başlatır
toplanti durum             # ilerlemeyi ve transkriptin son satırlarını gösterir
toplanti durdur            # kaydı bitirir; yazıya dökme kalanları tamamlayıp kapanır
```

Toplantı başlamadan önce `toplanti baslat` demeniz yeterli; sessiz kısımlar kaydedilmediği için erken başlatmanın bir zararı yok. Kayıtlar varsayılan olarak `kayitlar/<tarih>/` klasörüne yazılır.

Sık kullanılan seçenekler:

| Seçenek | Açıklama |
|---|---|
| `--klasor D:\toplanti\gun1` | Kayıt klasörü |
| `--sozluk sozluk.txt` | Doğru yazılması gereken isim ve kısaltmalar, her satıra bir tane (örnek: `sozluk_ornek.txt`) |
| `--dil tr --model small` | Ana konuşma dili Türkçe ise. `small.en` yalnızca İngilizce bilir; başka dillerde `small`, `medium` ya da `large-v3` kullanın |
| `--diger-diller ""` | Arapça/Fransızca dökümü kapatır. Bu döküm yavaştır: 2 dakikalık parça yaklaşık 3-4 dakikada işlenir |
| `--mikrofon` | Kendi mikrofonunuzu da ayrı kaydeder; transkriptte `BEN` olarak görünür |
| `--cihaz Hoparlör` | Yalnızca adında bu ifade geçen çıkışı dinler |

## Oluşan dosyalar

| Dosya | İçerik |
|---|---|
| `transkript.txt` | `[ss:dd:sn] KARŞI TARAF: metin`. Süre, kaydın başlangıcından itibaren sayılır; başlangıç zamanı `baslangic.txt` dosyasında saklanır |
| `transkript_diger.txt` | Arapça/Fransızca kısımlar, orijinal dilinde |
| `karsi_XXXX_<sn>.wav` | Ses parçaları |
| `*_log.txt` | Süreçlerin çıktıları, sorun olursa ilk bakılacak yer |

Süreçler yarıda kesilirse aynı klasörle `toplanti baslat --klasor ...` komutunu yeniden çalıştırın; zaman ekseni ve işlenmiş parçalar korunur.

## Not alma (Claude Code ile)

Transkript ham metindir. Okunabilir notlara çevirmek için toplantı sırasında [Claude Code](https://claude.com/claude-code) açıkken örneğin şunu yazabilirsiniz:

> `kayitlar/2026-11-10/transkript.txt` dosyasını takip et, yeni satırlar geldikçe oturum ve konuşmacı başlıklarıyla Türkçe notları `notlar.md` dosyasına yaz. Arapça kısımlar `transkript_diger.txt` içinde.

Gündem PDF'i varsa onu da verin. Konuşmacı adları ve oturum başlıkları böylece daha doğru çıkar.

## Bilinen sınırlamalar

- Kim konuştu ayrımı yok; tüm uzak ses `KARŞI TARAF` olarak geçer. Konuşmacıyı bağlamdan çıkarmak gerekiyor.
- Aksanlı İngilizce bazen başka bir dil sanılabilir. Bu yüzden ikinci döküm yalnızca `--diger-diller` ile seçilen dilleri işler.
- Bilgisayarın ses seviyesi kapalıysa ya da toplantı sekmesi sessize alınmışsa hiçbir şey kaydedilmez. `toplanti cihazlar` ile kontrol edin.
- Toplantı kaydetmeden önce katılımcıların ve düzenleyicinin onayını almak sizin sorumluluğunuzdadır.

## Lisans

MIT. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.
