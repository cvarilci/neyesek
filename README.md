# Neyesek 🍲

Evdeki malzemelerle "bu akşam ne pişirsem?" sorusuna hızlı cevap bulan web uygulaması.

Proje kuralları için [`CLAUDE.md`](CLAUDE.md), fazlar ve kabul kriterleri için [`PLAN.md`](PLAN.md) dosyalarına bakın.

## Teknoloji yığını

- Python 3.13 / Django 5.2
- Supabase PostgreSQL (yalnızca Django ORM ile), yerelde `.env` tanımsızsa SQLite
- Django şablonları + saf HTML/CSS/JS (framework yok)
- Statik dosyalar: WhiteNoise (yerelde), üretimde Vercel CDN
- Yayın: Vercel (`*.vercel.app`, ücretli domain yok)

## Yerel kurulum

1. Sanal ortam oluştur ve etkinleştir:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Bağımlılıkları kur:

   ```bash
   pip install -r requirements.txt
   ```

3. `.env.example` dosyasını `.env` olarak kopyala ve kendi değerlerini yaz:

   ```bash
   cp .env.example .env
   ```

   - `SECRET_KEY`: aşağıdaki komutla üret:

     ```bash
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```

   - `DEBUG=True` (yerel geliştirme için)
   - `ALLOWED_HOSTS=127.0.0.1,localhost`
   - `CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000`
   - `DATABASE_URL`: Supabase kullanacaksan **Project Settings → Database → Connection string → Transaction pooler** (port 6543) adresini yapıştır. Boş bırakırsan otomatik olarak yerel SQLite veritabanı (`db.sqlite3`) kullanılır.

4. Veritabanı tablolarını oluştur:

   ```bash
   python manage.py migrate
   ```

5. Hız sınırlama (`ACCOUNT_RATE_LIMITS`) sayaçlarının tutulduğu önbellek tablosunu oluştur
   (yalnızca bir kere; `migrate` bunu otomatik yapmaz):

   ```bash
   python manage.py createcachetable
   ```

6. Alerjen, malzeme grubu, kategori, malzeme ve tarif seed verisini yükle (tekrar çalıştırılırsa kayıt çoğaltmaz):

   ```bash
   python manage.py seed_recipes
   ```

7. Geliştirme sunucusunu başlat:

   ```bash
   python manage.py runserver
   ```

   Tarayıcıda [http://127.0.0.1:8000](http://127.0.0.1:8000) adresini aç.

8. Admin panelinde çalışmak için yönetici kullanıcı oluştur:

   ```bash
   python manage.py createsuperuser
   ```

## Testler

```bash
python manage.py test
```

> Not: Testler Supabase'in transaction-mode pooler'ı (port 6543) yerine SQLite'a karşı çalışır, çünkü PgBouncer transaction modu Django'nun test veritabanı oluşturma/silme akışıyla uyumlu değildir. `DATABASE_URL` tanımlıyken testleri açıkça SQLite'a zorlamak için:
>
> ```bash
> DATABASE_URL= python manage.py test
> ```

## Supabase notları

- Vercel sunucusuz çalıştığı için **connection pooler** (transaction mode, port 6543) adresi kullanılır.
- Migration'lar Vercel'de çalışmaz; her zaman yerelden, Supabase veritabanına karşı çalıştırılır.
- Aynı nedenle (`DROP DATABASE`/`CREATE DATABASE` pooler ile uyumsuz) `python manage.py test` de SQLite'a karşı çalıştırılır.
- `.env` dosyası asla commit edilmez (`.gitignore` içinde).

## Vercel'e yayın

Hedef: ücretli bir domain almadan, Vercel'in verdiği `https://<proje-adı>.vercel.app`
adresini seçtiğin kişilerle paylaşmak. Vercel Django projesini `manage.py` ve
`config/wsgi.py` üzerinden otomatik algılar; ekstra bir build betiğine gerek yoktur
(statik dosyalar `STATIC_ROOT` sayesinde build sırasında otomatik toplanıp Vercel'in
CDN'inden sunulur).

1. **Vercel hesabı ve proje bağlantısı**
   - [vercel.com](https://vercel.com) adresinde GitHub hesabınla giriş yap.
   - "Add New… → Project" ile `cvarilci/neyesek` deposunu içe aktar (GitHub App izni ister, onayla).
   - Framework Preset alanı otomatik "Django" olarak algılanmalı; algılanmazsa elle "Other" seçip devam edebilirsin, `vercel.json` zaten devrede.

2. **Ortam değişkenlerini gir** (Project Settings → Environment Variables, **Production** hedefiyle; değerleri Vercel panelinden elle gir, buraya yazma):
   - `SECRET_KEY` — yerelde ürettiğin komutla yeni ve **farklı** bir değer üret, `.env`'dekiyle aynı olmasın.
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` — ilk deploy'dan sonra Vercel'in verdiği adres, örn. `neyesek.vercel.app`
   - `CSRF_TRUSTED_ORIGINS` — şema dahil, örn. `https://neyesek.vercel.app`
   - `DATABASE_URL` — Supabase **Transaction pooler** (port 6543) bağlantı adresi

   İlk deploy'dan önce `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` için geçici olarak Vercel'in
   proje adına göre tahmini adresi (örn. `neyesek.vercel.app`) girebilirsin; gerçek adres
   farklı çıkarsa ilk deploy sonrası değeri güncelleyip yeniden deploy edersin.

   > **Önemli:** `SECRET_KEY` yalnızca çalışma zamanında değil, **build sırasında da**
   > gerekli — Vercel, WSGI giriş noktasını bulmak için build adımında `config/settings.py`
   > dosyasını içe aktarır. `SECRET_KEY` eksikse ilk deploy build aşamasında hemen hata verir.
   > Bu yüzden env değişkenlerini deploy'dan **önce** girmiş olmak gerekir.

3. **Veritabanını yerelden hazırla** (Vercel'de migration çalışmaz — `DATABASE_URL`'in
   `.env`'de Supabase'e işaret ettiğinden emin ol):

   ```bash
   python manage.py migrate
   python manage.py createcachetable
   python manage.py seed_recipes
   ```

   `createcachetable` çalıştırılmazsa giriş/kayıt/şifre sıfırlama sayfaları (hız
   sınırlama tablosu yok diye) `500` hatası verir — atlama.

4. **Deploy et**: Vercel projesini GitHub reposuna bağladıktan sonra `main` dalına her
   `git push` otomatik yeni bir production deploy'u tetikler. İlk deploy'u panelden de
   tetikleyebilirsin.

5. **`django.contrib.sites` kaydını güncelle** (yalnızca ilk deploy sonrası, bir kere):
   Üretim veritabanında (Supabase) `/admin/sites/site/1/` üzerinden `domain` alanını
   gerçek Vercel adresine (örn. `neyesek.vercel.app`, şema olmadan) güncelle. Bu adres
   yanlışsa şifre sıfırlama e-postalarındaki bağlantılar yanlış adrese gider.

6. **Yayından sonra kontrol listesi**:
   - `https://<proje-adı>.vercel.app/` ana akış: malzeme seç → sonuç → tarif detayı → alışveriş listesi
   - `/hesap/login/` ile giriş ve kayıt
   - Statik dosyalar (CSS/JS) yükleniyor mu, tarayıcı konsolunda 404 yok mu
   - `/admin/` erişimi ve `DEBUG=False` iken hatalı bir sayfanın (örn. olmayan bir tarif slug'ı) ayrıntı sızdırmadan sade 404 göstermesi
   - Google ile giriş **yok** (Faz 4'te kapsam dışı bırakıldı); Vercel'e taşırken ek bir işlem gerekmiyor.

> **Bilinen sınır:** `EMAIL_BACKEND` hâlâ konsol backend'i (Faz 4'ten beri değişmedi).
> Üretimde "şifremi unuttum" e-postaları gerçekten hiçbir yere gönderilmez, yalnızca
> Vercel'in fonksiyon loglarına yazılır — kullanıcı bu bağlantıya erişemez. Kayıt ve
> normal giriş etkilenmez (e-posta doğrulama zorunlu değil). Gerçek bir e-posta
> servisi (örn. Resend, Postmark, SMTP) eklemek ayrı bir karar ve yeni bir hesap/anahtar
> gerektirir; bu Faz 5'in kapsamına alınmadı, istenirse ayrıca yapılır.

### Ortam değişkenleri özeti

| Değişken | Yerel (.env) | Vercel (Production) |
|---|---|---|
| `SECRET_KEY` | kendi ürettiğin değer | **farklı**, kendi ürettiğin değer |
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | `<proje-adı>.vercel.app` |
| `CSRF_TRUSTED_ORIGINS` | `http://127.0.0.1:8000` | `https://<proje-adı>.vercel.app` |
| `DATABASE_URL` | boş (SQLite) veya Supabase | Supabase transaction pooler (6543) |
