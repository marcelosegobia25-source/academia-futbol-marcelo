import pytest

from app import create_app
from app.extensions import db
from config import Config


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    AUTO_BACKUP = False
    AUTH_REQUIRED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture()
def app(tmp_path):
    TestConfig.DOWNLOAD_FOLDER = str(tmp_path / "Descargas")
    TestConfig.UPLOAD_FOLDER = str(tmp_path / "uploads" / "alumnos")
    TestConfig.BRAND_FOLDER = str(tmp_path / "branding")
    TestConfig.DOCUMENT_FOLDER = str(tmp_path / "comprobantes")
    aplicacion = create_app(TestConfig)
    with aplicacion.app_context():
        yield aplicacion
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
