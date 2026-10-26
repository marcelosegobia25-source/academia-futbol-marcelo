from datetime import date
import pytest
from app.extensions import db
from app.models import Alumno, Tutor, PersonalDeportivo, Proveedor, Configuracion, Categoria
from app.utils.validacion import ErrorValidacion, solo_numeros_opcional


def test_solo_numeros_opcional_utilidad():
    # Valores vacíos o None
    assert solo_numeros_opcional(None, "CI") is None
    assert solo_numeros_opcional("", "CI") is None
    assert solo_numeros_opcional("   ", "CI") is None

    # Valores válidos
    assert solo_numeros_opcional("12345678", "CI") == "12345678"
    assert solo_numeros_opcional(12345678, "CI") == "12345678"
    assert solo_numeros_opcional(" 71234567 ", "Teléfono") == "71234567"

    # Valores inválidos con letras o caracteres especiales
    with pytest.raises(ErrorValidacion, match="solo debe contener números"):
        solo_numeros_opcional("1234ABC", "CI")

    with pytest.raises(ErrorValidacion, match="solo debe contener números"):
        solo_numeros_opcional("ABC1234", "CI")

    with pytest.raises(ErrorValidacion, match="solo debe contener números"):
        solo_numeros_opcional("7123-4567", "Teléfono")

    with pytest.raises(ErrorValidacion, match="solo debe contener números"):
        solo_numeros_opcional("+59171234567", "Teléfono")


def test_modelo_alumno_rechaza_letras_en_ci_y_telefono(app):
    with app.app_context():
        # Rechaza letras en CI
        with pytest.raises(ValueError):
            Alumno(
                nombre="Test", apellido="Numerico", fecha_nacimiento=date(2014, 1, 1),
                ci="1234ABC",
            )

        # Rechaza letras en Teléfono
        with pytest.raises(ValueError):
            Alumno(
                nombre="Test", apellido="Numerico", fecha_nacimiento=date(2014, 1, 1),
                telefono="7123456X",
            )

        # Acepta números válidos
        alumno = Alumno(
            nombre="Valido", apellido="Numerico", fecha_nacimiento=date(2014, 1, 1),
            ci="88990011", telefono="71234567",
        )
        assert alumno.ci == "88990011"
        assert alumno.telefono == "71234567"


def test_modelo_tutor_rechaza_letras_en_documento_y_telefono(app):
    with app.app_context():
        with pytest.raises(ValueError):
            Tutor(nombre="Tutor Test", documento="4589210-A")

        with pytest.raises(ValueError):
            Tutor(nombre="Tutor Test", telefono="76543210-Cel")

        tutor = Tutor(nombre="Tutor Test", documento="4589210", telefono="76543210")
        assert tutor.documento == "4589210"
        assert tutor.telefono == "76543210"


def test_modelo_personal_deportivo_rechaza_letras(app):
    with app.app_context():
        with pytest.raises(ValueError):
            PersonalDeportivo(nombre="Entrenador", documento="DOC-1234")

        with pytest.raises(ValueError):
            PersonalDeportivo(nombre="Entrenador", telefono="TEL-71234567")

        profe = PersonalDeportivo(nombre="Entrenador", documento="7894561", telefono="71234567")
        assert profe.documento == "7894561"
        assert profe.telefono == "71234567"


def test_modelo_proveedor_rechaza_letras(app):
    with app.app_context():
        with pytest.raises(ValueError):
            Proveedor(nombre="Proveedor Test", documento="NIT-12345")

        with pytest.raises(ValueError):
            Proveedor(nombre="Proveedor Test", telefono="7123456A")

        prov = Proveedor(nombre="Proveedor Test", documento="123456789", telefono="71234567")
        assert prov.documento == "123456789"
        assert prov.telefono == "71234567"


def test_modelo_configuracion_rechaza_letras_en_telefono(app):
    with app.app_context():
        config = Configuracion.obtener()
        with pytest.raises(ValueError):
            config.telefono = "71234567-Int"

        config.telefono = "71234567"
        assert config.telefono == "71234567"


def test_formulario_alumno_rechaza_letras_en_ci_y_telefono(client):
    respuesta = client.post(
        "/alumnos/nuevo",
        data={
            "nombre": "Carlos",
            "apellido": "Letras",
            "fecha_nacimiento": "2014-01-01",
            "ci": "1234ABC",
            "estado": "Activo",
            "beca": "Ninguna",
        },
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert "solo debe contener números".encode() in respuesta.data
    assert Alumno.query.filter_by(nombre="Carlos", apellido="Letras").first() is None

    # Ahora con teléfono con letras
    respuesta_tel = client.post(
        "/alumnos/nuevo",
        data={
            "nombre": "Carlos",
            "apellido": "Letras",
            "fecha_nacimiento": "2014-01-01",
            "telefono": "7123456A",
            "estado": "Activo",
            "beca": "Ninguna",
        },
        follow_redirects=True,
    )
    assert respuesta_tel.status_code == 200
    assert "solo debe contener números".encode() in respuesta_tel.data
    assert Alumno.query.filter_by(nombre="Carlos", apellido="Letras").first() is None
