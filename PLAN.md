# PLAN.md — Neyesek Geliştirme Planı

Proje kuralları için `CLAUDE.md` dosyasına bak. Bu dosya fazları, görevleri ve kabul kriterlerini içerir.

Her fazın sonunda **"Claude Code'a verilecek prompt"** bölümü var. O fazı başlatmak için bu metni Claude Code'a yapıştırman yeterli.

---

## Genel akış

```
Faz 0  Kurulum ──► Faz 1  Veri modeli + seed ──► Faz 2  Ana akış
                                                      │
Faz 5  Güvenlik + Vercel ◄── Faz 4  Üyelik ◄── Faz 3  Tasarım
```

Kullanıcı deneyimi (Faz 2 sonunda çalışır olacak):

1. Ana sayfa: "Bu akşam evde neler var?" Kullanıcı malzeme yazar, otomatik tamamlamadan seçer, seçtikleri chip olarak görünür.
2. İsteğe bağlı filtreler: süre (15 / 30 / 45 dk) ve kategori.
3. "Tarifleri göster" butonu.
4. Sonuçlar iki grupta listelenir: **Hemen yapabilirsin** (eksik malzeme yok) ve **1–3 malzeme alırsan** (eksikler kartta yazılı).
5. Tarif detayı: malzemeler (evde olanlar işaretli, eksikler vurgulu), adımlar, süre ve porsiyon, alerjen rozetleri.
6. "Eksikleri listeye ekle" butonu ile eksik malzemeler alışveriş listesine eklenir.

---

## Faz 0 — Kurulum

**Amaç:** Boş repodan yerelde çalışan bir Django iskeleti çıkarmak ve Supabase bağlantısını doğrulamak.

### Kullanıcının önceden yapacakları
- [x] GitHub'da `neyesek` reposu açıldı: `https://github.com/cvarilci/neyesek.git`
- [x] Masaüstündeki `neyesek` klasöründe `CLAUDE.md` ve `PLAN.md` hazır.
- [ ] Bilgisayarında git kimlik bilgilerinin tanımlı olduğunu kontrol et (`git config user.name`, `git config user.email`; GitHub'a push için tarayıcıyla giriş, GitHub CLI `gh auth login` ya da kişisel erişim token'ı).
- [ ] Supabase'de yeni proje oluştur. **Project Settings → Database → Connection string** bölümünden **Transaction pooler** (port 6543) adresini kopyala. Bu adresi yalnızca `.env` dosyasına yazacaksın, sohbete yapıştırma.

### Görevler
- [x] **Git kurulumu** (klasör henüz git deposu değil):
  - `git init -b main`
  - `git remote add origin https://github.com/cvarilci/neyesek.git`
  - `git fetch origin` ile uzak depoyu kontrol et. Uzak depo boşsa doğrudan devam et. İçinde README veya LICENSE gibi dosyalar varsa `git pull origin main --allow-unrelated-histories` ile birleştir; çakışma çıkarsa dur ve kullanıcıya sor.
  - `.gitignore` dosyasını **ilk commit'ten önce** oluştur.
  - İlk commit yalnızca `.gitignore`, `CLAUDE.md` ve `PLAN.md` içersin: `docs: proje planı ve kuralları`. Ardından `git push -u origin main`.
- [x] Sanal ortam (`.venv`) ve `requirements.txt` (Django, dj-database-url, python-dotenv, psycopg[binary], whitenoise)
- [x] `config` adlı Django projesi ve `recipes` uygulaması
- [x] Ayarları `.env` dosyasından okuyan `settings.py` (`SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`)
- [x] `DATABASE_URL` yoksa SQLite'a düşen yapı; Supabase için `CONN_MAX_AGE=0` ve `DISABLE_SERVER_SIDE_CURSORS=True`
- [x] `LANGUAGE_CODE = "tr"`, `TIME_ZONE = "Europe/Istanbul"`
- [x] Değer içermeyen `.env.example` (`.gitignore` git kurulumunda oluşturuldu; `.env`, `.venv/`, `db.sqlite3`, `__pycache__/`, `staticfiles/` içermeli)
- [x] WhiteNoise ayarı, `templates/` ve `static/` klasörleri
- [x] "Neyesek yakında 🍲" yazan basit bir `base.html` ve ana sayfa
- [x] Kurulum adımlarını anlatan `README.md`

### Kabul kriterleri
- `python manage.py runserver` ile `http://127.0.0.1:8000` açılıyor.
- `python manage.py migrate` Supabase veritabanına karşı hatasız çalışıyor ve tablolar Supabase panelinde görünüyor.
- `.env` git'e eklenmemiş, `git status` içinde görünmüyor.
- GitHub'daki repoda iki commit görünüyor: plan dosyaları ve Faz 0 iskeleti. `.env` dosyası GitHub'da yok.

### Claude Code'a verilecek prompt
```
CLAUDE.md ve PLAN.md dosyalarını oku. Sadece Faz 0'ı uygula.
Django projesinin adı "config", ilk uygulama "recipes" olsun.
.env.example oluştur ama gerçek değer yazma; ben .env dosyasını kendim dolduracağım.
Bittiğinde çalıştırmam gereken komutları sırayla yaz, kabul kriterlerini kontrol et
ve güvenlik açısından kısa bir gözden geçirme yap.
Kurulum commit'lerini ve push'u PLAN.md'deki Git kurulumu adımlarına göre yap. Faz 1'e geçme.
```

---

## Faz 1 — Veri modeli ve seed tarifler

**Amaç:** Tarif ve malzeme veritabanını kurmak, admin panelinden yönetilebilir hale getirmek, 40–60 tarifle doldurmak.

### Modeller (`recipes/models.py`)

| Model | Alanlar |
|---|---|
| `Allergen` | `code` (gluten, sut, yumurta, kuruyemis, yer_fistigi, balik, kabuklu_deniz, soya, susam, kereviz, hardal), `name`, `emoji` |
| `IngredientGroup` | `name` (Sebze, Meyve, Et-Tavuk-Balık, Süt ürünleri, Bakliyat, Tahıl-Hamur, Baharat-Sos, Diğer), `order` |
| `Ingredient` | `name`, `slug`, `group` (FK), `synonyms` (virgülle ayrılmış metin, örn. "domatesler, çeri domates"), `is_staple` (bool: tuz, su, sıvı yağ, karabiber gibi her evde var sayılanlar), `allergens` (M2M) |
| `Category` | `name` (Çorba, Tek tava, Makarna, Sebze yemeği, Et-Tavuk, Bakliyat, Yumurtalı, Salata, Hamur işi), `slug`, `emoji`, `order` |
| `Recipe` | `title`, `slug`, `summary` (tek cümle), `category` (FK), `prep_minutes`, `cook_minutes`, `servings`, `difficulty` (kolay / orta), `emoji`, `steps` (satır satır metin), `tips` (opsiyonel), `is_published`, `created_at` |
| `RecipeIngredient` | `recipe`, `ingredient`, `amount` (metin: "2 adet", "1 su bardağı"), `is_optional` |

- `Recipe.total_minutes` bir özellik (`property`) olarak hesaplanır.
- `Recipe.allergens` bir özellik olarak malzemelerin alerjenlerinden türetilir; ayrıca elle girilmez.

### Görevler
- [x] Modeller, `verbose_name` alanları Türkçe, `__str__` metotları
- [x] Admin: `RecipeIngredient` satır içi (inline), arama ve filtreler, slug otomatik doldurma
- [x] `normalize_tr()` ve Türkçe slug yardımcı fonksiyonları (`recipes/utils.py`)
- [x] Seed verisi `recipes/fixtures/` altında: alerjenler, malzeme grupları, **yaklaşık 120 malzeme**, kategoriler, **40–60 tarif**
- [x] Tarif seçim ölçütleri: toplam süre çoğunlukla 45 dakikanın altında, gerçekçi Türk ev yemekleri (menemen, mercimek çorbası, tavuk sote, fırın makarna, kıymalı patates, zeytinyağlı fasulye vb.), her tarif 4–10 malzeme ve 3–8 adım
- [x] Tek komutla yükleme: `python manage.py loaddata ...` ya da `python manage.py seed_recipes` yönetim komutu
- [x] Model testleri: toplam süre, alerjen türetme, `normalize_tr()`

### Kabul kriterleri
- Admin panelinden tarifler malzemeleriyle birlikte görüntülenip düzenlenebiliyor.
- Seed komutu boş veritabanına hatasız yükleniyor; ikinci kez çalıştırılınca kayıtları çoğaltmıyor.
- `python manage.py test` başarılı.

### Claude Code'a verilecek prompt
```
Faz 1'i uygula. PLAN.md içindeki model tablosuna uy.
Seed tarifleri gerçekçi, çalışan bir kişinin akşam yapabileceği pratik Türk ev yemekleri olsun;
malzeme miktarları ve adımlar mantıklı ve tutarlı olsun. Her tarifin malzemesi
malzeme tablosunda mutlaka bulunsun. Seed işlemi tekrar çalıştırılınca kayıt çoğaltmasın.
Bittiğinde komutları, kaç tarif ve malzeme eklendiğini ve test sonuçlarını yaz. Commit'le ve push et (CLAUDE.md → Git akışı). Faz 2'ye geçme.
```

---

## Faz 2 — Ana akış: malzeme seç, tarif bul

**Amaç:** Uygulamanın kalbini çalışır hale getirmek. Tasarım şimdilik sade olabilir; Faz 3'te güzelleşecek.

### Eşleştirme mantığı (`recipes/services.py`)

```
girdi: seçilen malzeme ID'leri, isteğe bağlı max_süre, isteğe bağlı kategori
her yayındaki tarif için:
    gerekli = zorunlu malzemeler − temel (is_staple) malzemeler
    evde_olan = gerekli ∩ seçilenler
    eksik = gerekli − seçilenler
    elenir: evde_olan boşsa (seçilenlerle hiç ilgisi olmayan tarif)
    elenir: len(eksik) > MAX_MISSING (varsayılan 3)
    elenir: süre veya kategori filtresine uymuyorsa
    skor = len(evde_olan) / len(gerekli)
sıralama: eksik sayısı (az → çok), skor (yüksek → düşük), toplam süre (kısa → uzun)
çıktı: iki grup → "hazır" (eksik = 0) ve "az_eksik" (1–3 eksik)
```

Veri seti küçük olduğu için eşleştirme Python tarafında yapılabilir. `prefetch_related` ile sorgu sayısını sabit tut (N+1 sorgu olmasın).

### Sayfalar ve uç noktalar

| Yol | Açıklama |
|---|---|
| `/` | Ana sayfa: malzeme arama kutusu, seçilen chip'ler, grup grup popüler malzemeler, süre ve kategori filtreleri |
| `/api/malzemeler/?q=dom` | JSON otomatik tamamlama (ad ve eş anlamlılarda `normalize_tr` ile arama, en fazla 10 sonuç) |
| `/tarifler/?m=domates,yumurta&sure=30&kategori=yumurtali` | Sonuç sayfası (paylaşılabilir URL). `m` parametresinde malzeme slug'ları bulunur, en fazla 30 adet. |
| `/tarif/<slug>/?m=...` | Tarif detayı: evde olan malzemeler ✓, eksikler vurgulu |
| `/alisveris-listesi/` | Alışveriş listesi (Faz 2'de tarayıcıda `localStorage` ile tutulur) |

### JavaScript (`static/js/app.js`, saf JS)
- Arama kutusunda 250 ms gecikmeli (debounce) `fetch` ile otomatik tamamlama, klavyeyle gezinme (↑ ↓ Enter Esc)
- Chip ekleme ve çıkarma; seçimler `localStorage` içinde saklanır, sayfa yenilense de kaybolmaz
- "Eksikleri listeye ekle", liste öğesini işaretleme ve silme, "Listeyi temizle"
- Kullanıcı verisini DOM'a `textContent` ile yaz, `innerHTML` kullanma

### Görevler
- [x] `services.py` eşleştirme fonksiyonu ve birim testleri (hazır, az eksik, elenen, temel malzeme, süre filtresi senaryoları)
- [x] Otomatik tamamlama JSON uç noktası
- [x] Ana sayfa, sonuç, detay ve alışveriş listesi şablonları
- [x] Geçersiz veya boş parametrelerde düzgün davranış (hata değil, yol gösteren boş durum mesajı)
- [x] Hiç sonuç çıkmazsa öneri: "Şu malzemelerden birini eklersen X tarif daha açılıyor" (opsiyonel, basit tut)

### Kabul kriterleri
- "yumurta, domates, biber" seçilince menemen "Hemen yapabilirsin" grubunda çıkıyor.
- Temel malzemeler (tuz, yağ) seçilmese de eksik sayılmıyor.
- 3 eksik malzemesi olan tarif "1–3 malzeme alırsan" grubunda görünüyor, 4 eksiği olan tarif listelenmiyor.
- "Dom", "DOM" ve "domatesler" aramaları domatesi buluyor; "ıspanak" ve "Ispanak" aynı sonucu veriyor.
- Alışveriş listesi sayfa yenilendikten sonra da duruyor.
- Sonuç sayfası sabit sayıda veritabanı sorgusuyla çalışıyor.
- Tüm testler geçiyor.

### Claude Code'a verilecek prompt
```
Faz 2'yi uygula. Eşleştirme mantığını PLAN.md'deki algoritmaya göre recipes/services.py içine yaz
ve önce testlerini yaz. Frontend saf HTML/CSS/JS olsun, framework ekleme.
Bu fazda tasarım sade kalabilir ama CLAUDE.md'deki CSS değişkenlerini şimdiden tanımla.
Bittiğinde kabul kriterlerini tek tek dene ve sonucu yaz. Commit'le ve push et (CLAUDE.md → Git akışı). Faz 3'e geçme.
```

---

## Faz 3 — Tasarım ve cilalama

**Amaç:** Arayüzü `CLAUDE.md` içindeki tasarım diline göre sıcak, canlı ve temiz hale getirmek.

### Görevler
- [x] `base.html`: üst çubuk (logo "Neyesek 🍲", alışveriş listesi ikonu ve sayaç rozeti), alt bilgi
- [x] Ana sayfa karşılama alanı: "Bu akşam ne pişirsek?" başlığı, samimi alt metin, yumuşak renk geçişli arka plan dekoru
- [x] Malzeme chip'leri: grup renkleriyle hafif tonlanmış, "×" ile kaldırma, ekleme anında küçük animasyon
- [x] Tarif kartları: büyük emoji, başlık, süre rozeti (⏱ 20 dk), kategori, "Hemen yapabilirsin" için nane rozeti, eksikler için şeftali rozeti
- [x] Tarif detayı: iki sütun (masaüstü) veya tek sütun (mobil); malzemelerde ✓ ve eksik işaretleri, numaralı adımlar, alerjen rozetleri
- [x] Alışveriş listesi: işaretlenince üstü çizilen öğeler, "Kopyala" butonu (listeyi WhatsApp'a yapıştırmak için düz metin)
- [x] Boş durum ekranları, yükleniyor göstergesi, 404 sayfası
- [x] Erişilebilirlik: `label` etiketleri, odak halkaları, `aria-live` ile otomatik tamamlama duyurusu, `prefers-reduced-motion` desteği
- [x] Favicon (emoji tabanlı SVG) ve `<meta>` açıklama etiketleri

### Kabul kriterleri
- 375px, 768px ve 1280px genişliklerde yatay kaydırma olmadan düzgün görünüyor.
- Metin kontrastı AA seviyesinde.
- Kodda sabit renk yok; tüm renkler CSS değişkenlerinden geliyor.

### Claude Code'a verilecek prompt
```
Faz 3'ü uygula. CLAUDE.md'deki tasarım diline ve renk değişkenlerine sadık kal.
Hedef kitle akşam telefondan bakan çalışan kullanıcılar; mobil öncelikli tasarla.
CSS framework ekleme. Bittiğinde hangi ekranları değiştirdiğini ve
mobil/masaüstü kontrollerini nasıl yaptığını yaz. Commit'le ve push et (CLAUDE.md → Git akışı). Faz 4'e geçme.
```

---

## Faz 4 — Üyelik ve kişisel veriler

**Amaç:** Üyelik olmadan her şey çalışmaya devam eder. Üye olan kullanıcı dolabını, favorilerini ve alışveriş listesini hesabında saklar.

### Kullanıcının önceden yapacakları
- [ ] Google Cloud Console'da OAuth istemcisi oluştur. Yetkili yönlendirme adresi (yerel): `http://127.0.0.1:8000/hesap/google/login/callback/`
- [ ] Client ID ve Secret değerlerini `.env` dosyasına yaz.

### Modeller (`accounts` uygulaması)
| Model | Alanlar |
|---|---|
| `Pantry` | `user` (OneToOne), `ingredients` (M2M), `updated_at` — "Dolabım" |
| `Favorite` | `user`, `recipe`, `created_at` (kullanıcı + tarif benzersiz) |
| `ShoppingItem` | `user`, `ingredient` (opsiyonel FK), `text`, `is_checked`, `created_at` |

### Görevler
- [ ] `django-allauth`: e-posta ile giriş (kullanıcı adı yok), şifre sıfırlama, Google ile giriş
- [ ] Geliştirmede e-postalar konsola yazılsın; gerçek e-posta servisi sonra eklenecek
- [ ] Giriş, kayıt ve şifre sıfırlama şablonları tasarım diline uygun ve Türkçe
- [ ] Giriş yapınca `localStorage` içindeki seçimler ve alışveriş listesi hesaba aktarılsın (bir kerelik birleştirme)
- [ ] "Dolabımı kaydet" ve "Dolabımdan başla" butonları
- [ ] Tarif kartında ve detayında favori (♥) butonu; `/favorilerim/` sayfası
- [ ] Giriş yapan kullanıcıda alışveriş listesi veritabanından gelsin (POST + CSRF ile güncellenir)
- [ ] Yetki testleri: bir kullanıcı başka birinin favori veya liste öğesine erişemiyor ve onu silemiyor

### Kabul kriterleri
- Üye olmadan Faz 2 ve 3'teki her şey aynen çalışıyor.
- E-posta/şifre ve Google ile kayıt ve giriş yerelde çalışıyor.
- Farklı tarayıcıdan giriş yapınca dolap, favoriler ve liste aynı şekilde geliyor.
- Yetki testleri geçiyor.

### Claude Code'a verilecek prompt
```
Faz 4'ü uygula. Kimlik doğrulama için django-allauth kullan, Supabase Auth kullanma.
Üyeliksiz kullanım bozulmamalı. Kullanıcıya ait her sorguyu request.user ile filtrele
ve bunun için yetki testleri yaz. Google OAuth anahtarlarını .env dosyasından oku.
Bittiğinde Google Console'da benim yapmam gereken ayarları da listele. Commit'le ve push et (CLAUDE.md → Git akışı). Faz 5'e geçme.
```

---

## Faz 5 — Güvenlik incelemesi ve Vercel'e yayın

**Amaç:** Uygulamayı güvenli bir üretim ayarıyla Vercel'e çıkarmak (ilk aşamada `*.vercel.app` adresiyle, domain almadan).

### Görevler
- [ ] Kapsamlı güvenlik ve doğruluk incelemesi: `CLAUDE.md` güvenlik kuralları, `python manage.py check --deploy` çıktısı, bağımlılık sürümleri. Bulgular önem sırasıyla raporlanır ve düzeltilir.
- [ ] Üretim ayarları: `DEBUG=False`, güvenlik başlıkları, HSTS, güvenli cookie'ler
- [ ] Giriş denemelerinde hız sınırı (allauth'un yerleşik `ACCOUNT_RATE_LIMITS` ayarı)
- [ ] Vercel yapılandırması: `vercel.json`, WSGI giriş noktası, statik dosyaların (`collectstatic` + WhiteNoise) sunulması. **Vercel'in güncel Python/Django belgelerini kontrol ederek** yapılandır.
- [ ] Vercel projesini GitHub'daki `cvarilci/neyesek` reposuna bağlama talimatı (her `main` push'u otomatik yayına çıkar)
- [ ] `ALLOWED_HOSTS` ve `CSRF_TRUSTED_ORIGINS` değişkenlerine Vercel adresini ekle
- [ ] Google OAuth yönlendirme adresine üretim adresini ekleme talimatı
- [ ] `README.md` içine yayın adımları: Vercel ortam değişkenleri, migration'ın yerelden çalıştırılması, seed verisi
- [ ] Yayından sonra kontrol listesi: ana akış, giriş, statik dosyalar, 404 sayfası, `/admin` erişimi

### Kabul kriterleri
- `python manage.py check --deploy` kritik uyarı vermiyor.
- Vercel adresinde tüm akış (malzeme seçimi → sonuç → detay → liste → giriş) çalışıyor.
- Tarayıcıda hata ayrıntısı veya sır sızdıran bir sayfa görünmüyor.

### Claude Code'a verilecek prompt
```
Faz 5'i uygula. Önce yayına almadan kapsamlı bir güvenlik ve doğruluk incelemesi yap,
bulguları önem sırasına göre raporla ve düzelt. Sonra Vercel yapılandırmasını hazırla;
Vercel'in güncel Python runtime belgelerine göre ilerle. Vercel paneline girmem gereken
ortam değişkenlerini (değerleri olmadan) ve adımları sırayla yaz.
Güvenlik düzeltmelerini ve Vercel yapılandırmasını ayrı commit'lerle kaydet ve push et
(CLAUDE.md → Git akışı). Vercel'i GitHub reposuna bağlarsam her push otomatik yayına çıkacak;
bu yüzden push'tan önce testlerin geçtiğinden emin ol.
```

---

## Sonraki fikirler (prototip sonrası)

- Yapay zekâ destekli öneri: dolaptaki malzemelere göre seed'de olmayan bir tarif önerisi
- Tarif görselleri (Supabase Storage)
- Haftalık menü planı ve planın tamamı için alışveriş listesi
- Puanlama ve "yaptım" işareti
- Kişi sayısına göre malzeme miktarlarını ölçekleme
- PWA: ana ekrana ekleme, çevrimdışı alışveriş listesi
- Özel domain
