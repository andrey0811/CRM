# Plant CRM — Users Module (Django Templates)

Server-side rendering loyiha: Django view + HTML template + forma. REST API yo'q.

## Tez boshlash (lokal, Docker siz)

```bash
# 1. Virtual muhit va paketlar
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt

# 2. Muhit o'zgaruvchilari
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS
# .env da DB_HOST=localhost qiling

# 3. PostgreSQL ishlayotgan bo'lishi kerak, keyin:
python manage.py migrate
python manage.py create_sample_users
python manage.py runserver
```

Brauzer: `http://127.0.0.1:8000/login/`

### Namuna login

| Tur | Email | Parol |
|-----|-------|-------|
| Admin | admin@test.com | adminpass123 |
| Xodim | employee@test.com | emplpass123 |

Xodim kirishida emailga 6 xonali kod yuboriladi (dev rejimida konsolga chiqadi).

## Docker bilan

```bash
copy .env.example .env
# .env da DB_HOST=db qiling

cd docker
docker-compose up --build
```

Migratsiya `web` servisi ishga tushganda avtomatik bajariladi.

Namuna foydalanuvchilar:

```bash
docker-compose exec web python manage.py create_sample_users
```

## Migratsiya buyruqlari

```bash
python manage.py makemigrations
python manage.py migrate
```

## Superuser (Django Admin uchun)

```bash
python manage.py createsuperuser
```

Django Admin: `http://127.0.0.1:8000/django-admin/`

## Sahifalar va URL lar

| URL | Tavsif |
|-----|--------|
| `/login/` | Admin va xodim login |
| `/verify-code/` | Xodim 2-bosqichli kod tasdiqlash |
| `/logout/` | Chiqish (POST) |
| `/dashboard/` | Asosiy sahifa |
| `/admin-panel/users/` | Foydalanuvchilar ro'yxati |
| `/admin-panel/users/create/` | Yangi foydalanuvchi |
| `/admin-panel/users/<id>/edit/` | Tahrirlash, bloklash, arxiv |
| `/admin-panel/users/<id>/force-logout/` | Majburiy chiqish (POST) |
| `/admin-panel/roles/` | Rollar ro'yxati |
| `/admin-panel/roles/<id>/` | Rol huquqlari (checkbox jadval) |
| `/django-admin/` | Standart Django Admin |

## Standart rollar

Migratsiya bilan yaratiladi (`is_system=True`):

| Rol | Default huquqlar |
|-----|------------------|
| **Front** | clients, tickets — read+write; catalog — read |
| **Bek** | catalog — read+write; clients — read |
| **Gibrid** | clients, catalog, tickets — read+write |
| **Kontent** | catalog — read+write |
| **Lokomotiv** | Barcha modullar — read; faqat tickets — write |

## Xususiyatlar

- **Custom User** — email orqali login, Django session auth
- **2 bosqichli xodim login** — email + parol + 6 xonali kod
- **WorkSession** — ish vaqti kuzatuvi
- **5 soat inaktivlik** — Celery task sessiyani yopadi
- **Anomaliya aniqlash** — 10 daqiqada 30+ `client.view` log → avtoblok
- **ActionLog** — barcha amallar loglanadi (`apps/common`)
- **require_permission** decorator — keyingi modullar uchun

## Testlar

```bash
# Lokal (SQLite, pytest)
pytest apps/users/tests/

# Yoki Django test runner
python manage.py test apps.users.tests
```

## Celery

Docker da `celery` servisi worker + beat ishga tushiradi:
- Har 10 daqiqada inaktiv sessiyalarni yopadi
- Anomaliya tekshiruvi (`ActionLog` da `client.view`)

## Keyingi modullar uchun

Permission decorator:

```python
from apps.users.decorators import require_permission

@require_permission('clients', 'read')
def client_list(request):
    ...
```

Mijoz kartochkasi ochilganda anomaliya logi:

```python
from apps.users.services import record_client_view
record_client_view(request.user, client_id, request)
```

## Muhit o'zgaruvchilari

Asosiy `.env` o'zgaruvchilari `.env.example` da:
- `SECRET_KEY`, `DB_*` — Django va PostgreSQL
- `EMAIL_*` — xodim tasdiqlash kodi
- `CELERY_*`, `REDIS_URL` — fon vazifalar
- `ANOMALY_*`, `INACTIVITY_LOGOUT_HOURS` — xavfsizlik
