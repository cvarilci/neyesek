# CLAUDE.md — Neyesek

Bu dosya Claude Code için kalıcı proje kurallarıdır. Her oturumda önce bu dosyayı, ardından `PLAN.md` dosyasını oku.

## Proje özeti

**Neyesek**, akşam işten eve dönen çalışanlar için "ne yemek yapsam?" sorusunu çözen bir web uygulamasıdır. Kullanıcı evinde olan malzemeleri seçer. Uygulama bu malzemelerle hemen yapılabilecek ya da 1–3 ek malzemeyle yapılabilecek pratik tarifleri önerir. Eksik malzemeler alışveriş listesine eklenebilir.

İlk hedef **çalışan bir prototip** çıkarmaktır. Basit tut, gereksiz soyutlama ve ağır bağımlılık ekleme.

## Teknoloji yığını (değiştirme)

- **Backend:** Python 3.12, Django 5.x
- **Veritabanı:** Supabase PostgreSQL, **yalnızca Django ORM ile** kullanılır. `supabase-py` ve Supabase Auth kullanılmaz.
- **Frontend:** Aynı repoda Django şablonları + saf HTML, CSS ve JavaScript. React, Vue, Tailwind, jQuery, npm build adımı **yok**.
- **Kimlik doğrulama (Faz 4):** Django auth + `django-allauth` (e-posta/şifre + Google)
- **Statik dosyalar:** WhiteNoise
- **Yayın:** Vercel (Python runtime)
- **Yardımcı paketler:** `dj-database-url`, `python-dotenv`, `psycopg[binary]`, `whitenoise`. Bunların dışında paket eklemeden önce gerekçesini söyle ve onay iste.

## Çalışma kuralları

1. **Faz faz ilerle.** Yalnızca istenen fazı yap. Faz bitince dur, yapılanları özetle, kabul kriterlerini tek tek kontrol et ve kullanıcıdan onay bekle. Bir sonraki faza kendiliğinden geçme.
2. Faz içinde belirsiz bir karar çıkarsa varsayım yapıp ilerleme; kısa bir soru sor.
3. Her faz sonunda çalıştırılacak komutları (migration, seed, runserver) açıkça yaz.
4. Her faz sonunda kodu güvenlik ve doğruluk açısından gözden geçir (aşağıdaki güvenlik kurallarına göre) ve bulguları raporla.
5. **Her fazın sonunda commit ve push yap** (aşağıdaki "Git akışı" bölümüne göre). Faz içinde de mantıklı ara noktalarda küçük commit'ler atabilirsin; push faz sonunda, kabul kriterleri sağlandıktan sonra yapılır.
6. `PLAN.md` içinde tamamlanan görevlerin kutucuklarını işaretle (`[x]`).

## Git akışı

- **Uzak depo:** `https://github.com/cvarilci/neyesek.git`, dal adı `main`. Prototip aşamasında ayrı dal açılmaz, doğrudan `main` üzerinde çalışılır.
- **Commit mesajı biçimi:** `tür: açıklama`. Türler: `feat`, `fix`, `chore`, `docs`, `test`, `style`, `refactor`. Açıklama Türkçe olabilir.
  - Faz sonu commit'i örneği: `feat: Faz 2 — malzeme seçimi ve tarif eşleştirme`
- **Push öncesi zorunlu kontroller** (sırasıyla):
  1. `PLAN.md` içinde tamamlanan görevler `[x]` olarak işaretlenmiş olmalı (bu değişiklik de faz commit'ine girer).
  2. `python manage.py test` başarılı olmalı (yalnızca plan dosyalarını içeren ilk commit hariç).
  3. `git status` çıktısını kontrol et. `.env`, `.venv/`, `db.sqlite3`, `__pycache__/`, `staticfiles/` gibi dosyalar sahnede (staged) **olmamalı**.
  4. `git diff --cached` içinde sır (şifre, anahtar, bağlantı adresi) olmadığını gözden geçir.
  5. Sorun yoksa `git commit` ve ardından `git push origin main`.
- Push kimlik doğrulama hatası verirse şifre veya token isteme; hatayı göster ve kullanıcının kendi git kimlik bilgilerini ayarlamasını iste.
- `git push --force`, `git reset --hard` ve geçmişi yeniden yazan komutları kullanıcı açıkça istemedikçe **kullanma**.
- Push'tan sonra kullanıcıya commit özetini ve `git log --oneline -5` çıktısını göster.

## Dil ve adlandırma

- **Kod** (model, değişken, fonksiyon, URL adı) **İngilizce**: `Recipe`, `Ingredient`, `match_recipes()`.
- **Kullanıcının gördüğü her metin Türkçe**: butonlar, başlıklar, hata mesajları, admin'deki `verbose_name` alanları.
- **URL yolları Türkçe ve sade**: `/tarifler/`, `/tarif/<slug>/`, `/alisveris-listesi/`.
- Kod yorumları Türkçe olabilir, kısa tut.
- Türkçe karakter normalizasyonuna dikkat et. Python'un `lower()` fonksiyonu `İ` ve `I` harflerini yanlış çevirir. Arama ve eşleştirme için `I→ı` ve `İ→i` dönüşümünü yapan bir `normalize_tr()` yardımcı fonksiyonu kullan. Slug üretiminde Türkçe harfleri ASCII karşılığına çevir.

## Klasör yapısı

```
neyesek/
├── manage.py
├── config/              # settings.py, urls.py, wsgi.py
├── recipes/             # tarif, malzeme, eşleştirme mantığı
│   ├── fixtures/        # seed JSON dosyaları
│   ├── services.py      # eşleştirme algoritması (view'lardan ayrı)
│   └── tests.py
├── accounts/            # Faz 4
├── templates/
│   ├── base.html
│   └── recipes/
├── static/
│   ├── css/main.css
│   └── js/app.js
├── requirements.txt
├── .env.example
├── .gitignore
├── vercel.json          # Faz 5
├── CLAUDE.md
├── PLAN.md
└── README.md
```

İş mantığını (özellikle eşleştirme) view'lara değil `services.py` içine yaz ve birim testlerle koru.

## Supabase ve Vercel ile ilgili kritik notlar

- Bağlantı adresi `.env` içindeki `DATABASE_URL` değişkeninden `dj-database-url` ile okunur.
- Vercel sunucusuz (serverless) çalıştığı için Supabase **connection pooler** adresini kullan: transaction mode, port **6543**.
- Ayarlarda `CONN_MAX_AGE = 0` ve `DISABLE_SERVER_SIDE_CURSORS = True` olmalı (pooler transaction mode ile uyum için).
- **Migration'lar Vercel'de çalıştırılmaz.** Yerelde, Supabase veritabanına karşı `python manage.py migrate` ile çalıştırılır.
- Vercel dosya sistemi kalıcı değildir. Kullanıcı dosya yüklemesi yok. Tarif görselleri prototipte emoji veya CSS illüstrasyonudur.
- Yerelde de Supabase veritabanı kullanılabilir. İstenirse geliştirme için SQLite'a düşülebilir: `DATABASE_URL` tanımlı değilse SQLite kullan.

## Güvenlik kuralları (her fazda geçerli)

- `SECRET_KEY`, `DATABASE_URL`, Google OAuth anahtarları gibi sırlar **yalnızca** `.env` içinde durur. `.env` dosyası `.gitignore` içinde olmalı. Repoda sadece değer içermeyen `.env.example` bulunur.
- Hiçbir sır koda, şablona, JavaScript'e ya da commit'e yazılmaz. Bir sır yanlışlıkla commit edilirse kullanıcıyı hemen uyar (anahtarın yenilenmesi gerekir).
- `DEBUG` değeri ortam değişkeninden okunur. Varsayılan `False` olmalı.
- `ALLOWED_HOSTS` ve `CSRF_TRUSTED_ORIGINS` ortam değişkeninden okunur.
- Ham SQL yazma. Zorunlu kalırsan parametreli sorgu kullan.
- Veri değiştiren tüm istekler POST olmalı ve CSRF korumalı olmalı. JavaScript `fetch` çağrılarında CSRF token'ı gönder.
- Şablonlarda `|safe` ve `mark_safe` kullanma. JavaScript'te kullanıcı verisini `innerHTML` ile basma; `textContent` veya DOM API kullan.
- Kullanıcıya ait veriler (Faz 4: dolap, favoriler, alışveriş listesi) her sorguda `request.user` ile filtrelenmeli. Başka kullanıcının kaydına ID ile erişilememeli.
- Query parametrelerini doğrula: sayısal değerleri `int` dönüşümüyle, listeleri uzunluk sınırıyla (örneğin en fazla 30 malzeme) kontrol et.
- Üretimde güvenlik ayarları açık olmalı: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `X_FRAME_OPTIONS = "DENY"`, `SECURE_CONTENT_TYPE_NOSNIFF`.

## Tasarım dili

Hedef: açık arka planlı, canlı renklerin yumuşak tonlarla kullanıldığı, sıcak, samimi ve temiz bir arayüz. Kadın kullanıcıların ilgisini çekecek, "mutfak defteri" hissi veren ama kalabalık olmayan bir görünüm.

**Renkler** (`static/css/main.css` içinde CSS değişkeni olarak tanımla, kodda sabit renk kullanma):

```css
:root {
  --bg:            #FFF8F5;  /* krem-pembe arka plan */
  --surface:       #FFFFFF;  /* kartlar */
  --surface-tint:  #FFEFEA;  /* hafif mercan tonlu alanlar */
  --primary:       #FF6B6B;  /* mercan — ana vurgu, ikon, dekor */
  --primary-dark:  #D94452;  /* üzerine beyaz yazı gelen butonlar */
  --accent:        #E84A8A;  /* fuşya — ikincil vurgu */
  --peach:         #FFB88C;  /* şeftali — rozet, etiket */
  --mint:          #3DBFB4;  /* "hemen yapabilirsin" durumu */
  --mint-soft:     #E3F7F5;
  --text:          #2D2A32;
  --text-muted:    #6E6873;
  --border:        #F1E4DF;
  --radius:        16px;
  --shadow:        0 4px 16px rgba(217, 68, 82, 0.08);
}
```

- **Font:** Google Fonts'tan **Nunito** (başlıklar 700–800, metin 400–600). Yedek font yığını: `system-ui, -apple-system, "Segoe UI", sans-serif`.
- **Mobil öncelikli:** Önce 375px genişlik için tasarla, sonra büyüt. Dokunma alanları en az 44px.
- Yuvarlatılmış köşeler, yumuşak gölgeler, bol boşluk. Keskin siyah ve gri tonlardan kaçın.
- Yazı ve arka plan kontrastı WCAG AA seviyesini (4.5:1) sağlamalı. Açık mercan zemin üzerine beyaz metin koyma; butonlarda `--primary-dark` kullan.
- İkonlar için emoji veya satır içi SVG kullan. İkon kütüphanesi ekleme.
- Boş durumlar (sonuç yok, liste boş) sevimli ve yol gösterici bir metinle tasarlanmalı.

## Kapsam dışı (şimdilik yapma)

Yapay zekâ ile tarif üretme, görsel yükleme, puanlama ve yorum, sosyal paylaşım, bildirim, mobil uygulama, ödeme. Bunlar prototipten sonra ayrıca planlanacak.
