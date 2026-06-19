import pytest


@pytest.fixture(scope='session')
def django_db_modify_db_settings():
    """Use SQLite for local tests without PostgreSQL."""
    return {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }


@pytest.fixture(autouse=True)
def use_locmem_email(settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
