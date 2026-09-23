# Neyesek 🍲

Evdeki malzemelerle "bu akşam ne pişirsem?" sorusuna hızlı cevap bulan web uygulaması.

Proje kuralları için [`CLAUDE.md`](CLAUDE.md), fazlar ve kabul kriterleri için [`PLAN.md`](PLAN.md) dosyalarına bakın.

## Teknoloji yığını

- Python 3.13 / Django 5.2
- Supabase PostgreSQL (yalnızca Django ORM ile), yerelde `.env` tanımsızsa SQLite
- Django şablonları + saf HTML/CSS/JS (framework yok)
- Statik dosyalar: WhiteNoise
- Yayın: Vercel (Faz 5)

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

5. Geliştirme sunucusunu başlat:

   ```bash
   python manage.py runserver
   ```

   Tarayıcıda [http://127.0.0.1:8000](http://127.0.0.1:8000) adresini aç.

6. Admin panelinde çalışmak için yönetici kullanıcı oluştur:

   ```bash
   python manage.py createsuperuser
   ```

## Testler

```bash
python manage.py test
```

## Supabase notları

- Vercel sunucusuz çalıştığı için **connection pooler** (transaction mode, port 6543) adresi kullanılır.
- Migration'lar Vercel'de çalışmaz; her zaman yerelden, Supabase veritabanına karşı çalıştırılır.
- `.env` dosyası asla commit edilmez (`.gitignore` içinde).
