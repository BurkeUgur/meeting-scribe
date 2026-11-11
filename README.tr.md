# meeting-scribe

[English](README.md)

Online toplantıların (Interactio, Zoom, Teams, Webex vb.) sesini **bilgisayarın ses çıkışından** kaydeder ve Whisper ile yerel olarak yazıya döker. Toplantı uygulamasına bağlanmaz, bot eklemez; hoparlöre ne geliyorsa onu kaydeder. Her şey bilgisayarınızda çalışır, ses hiçbir yere gönderilmez.

- Ses 2 dakikalık parçalar hâlinde kaydedilir. Sessiz parçalar (aralar) kaydedilmez.
- Yazıya dökme kayıtla eş zamanlı ilerler; transkript her parçada güncellenir.
- Tüm ses çıkışları aynı anda dinlenir. Toplantı sırasında kulaklık ya da harici hoparlör değiştirseniz de kayıt kesilmez.
- Çeviri kanalı yerine salon sesi gelirse ve konuşmacı Arapça ya da Fransızca konuşursa, bu kısımlar çok dilli bir modelle orijinal dilinde ayrıca yazıya dökülür.

> Yalnızca Windows'ta denendi. Ses çıkışını kaydetmek için `SoundCard` kütüphanesinin loopback desteği kullanılıyor; macOS'te bu desteklenmiyor.

## Kurulum

Python 3.9 veya üstü gerekir.

```
pip install git+https://github.com/BurkeUgur/meeting-scribe.git
```

Modeller ilk kullanımda otomatik indirilir: ana dil için `small.en` yaklaşık 500 MB, Arapça/Fransızca için `large-v3` yaklaşık 3 GB.

## Kullanım

```
scribe devices     # ses çıkışlarını listeler, hangisinden ses geldiğini ölçer
scribe start       # kaydı ve yazıya dökmeyi arka planda başlatır
scribe status      # ilerlemeyi ve transkriptin son satırlarını gösterir
scribe stop        # kaydı bitirir; yazıya dökme kalanları tamamlayıp kapanır
```

Toplantı başlamadan önce `scribe start` demeniz yeterli; sessiz kısımlar kaydedilmediği için erken başlatmanın bir zararı yok. Kayıtlar varsayılan olarak `recordings/<tarih>/` klasörüne yazılır.

`scribe start` için sık kullanılan seçenekler:

| Seçenek | Açıklama |
|---|---|
| `--dir D:\toplanti\gun1` | Kayıt klasörü |
| `--glossary sozluk.txt` | Doğru yazılması gereken isim ve kısaltmalar, her satıra bir tane (örnek: `glossary_example.txt`) |
| `--lang tr --model small` | Ana konuşma dili Türkçe ise. `small.en` yalnızca İngilizce bilir; başka dillerde `small`, `medium` ya da `large-v3` kullanın |
| `--extra-langs ""` | Arapça/Fransızca dökümü kapatır. Bu döküm yavaştır: 2 dakikalık parça yaklaşık 3-4 dakikada işlenir |
| `--mic` | Kendi mikrofonunuzu da ayrı kaydeder; transkriptte `ME` olarak görünür |
| `--device Hoparlör` | Yalnızca adında bu ifade geçen çıkışı dinler |

## Oluşan dosyalar

| Dosya | İçerik |
|---|---|
| `transcript.txt` | `[ss:dd:sn] REMOTE: metin`. Süre, kaydın başlangıcından itibaren sayılır; başlangıç zamanı `start_time.txt` dosyasında saklanır |
| `transcript_other.txt` | Arapça/Fransızca kısımlar, orijinal dilinde |
| `remote_XXXX_<sn>.wav` | Ses parçaları |
| `*_log.txt` | Süreçlerin çıktıları, sorun olursa ilk bakılacak yer |

Süreçler yarıda kesilirse aynı klasörle `scribe start --dir ...` komutunu yeniden çalıştırın; zaman ekseni ve işlenmiş parçalar korunur.

## Not alma (Claude Code ile)

Transkript ham metindir. Okunabilir notlara çevirmek için toplantı sırasında [Claude Code](https://claude.com/claude-code) açıkken örneğin şunu yazabilirsiniz:

> `recordings/2026-11-10/transcript.txt` dosyasını takip et, yeni satırlar geldikçe oturum ve konuşmacı başlıklarıyla Türkçe notları `notlar.md` dosyasına yaz. Arapça kısımlar `transcript_other.txt` içinde.

Gündem PDF'i varsa onu da verin. Konuşmacı adları ve oturum başlıkları böylece daha doğru çıkar.

## Bilinen sınırlamalar

- Kim konuştu ayrımı yok; tüm uzak ses `REMOTE` olarak geçer. Konuşmacıyı bağlamdan çıkarmak gerekiyor.
- Aksanlı İngilizce bazen başka bir dil sanılabilir. Bu yüzden ikinci döküm yalnızca `--extra-langs` ile seçilen dilleri işler.
- Bilgisayarın ses seviyesi kapalıysa ya da toplantı sekmesi sessize alınmışsa hiçbir şey kaydedilmez. `scribe devices` ile kontrol edin.
- Toplantı kaydetmeden önce katılımcıların ve düzenleyicinin onayını almak sizin sorumluluğunuzdadır.

## Lisans

MIT. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.
