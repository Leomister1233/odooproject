import base64
import ctypes
from ctypes import wintypes

from django.conf import settings
from django.db import migrations, models


CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def build_blob(raw_bytes):
    if not raw_bytes:
        return DATA_BLOB(0, None), None

    buffer = ctypes.create_string_buffer(raw_bytes, len(raw_bytes))
    blob = DATA_BLOB(len(raw_bytes), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return blob, buffer


def read_blob(blob):
    if not blob.cbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def encrypt_secret(value):
    if not value:
        return ""

    plain_blob, plain_buffer = build_blob(str(value).encode("utf-8"))
    entropy_blob, entropy_buffer = build_blob(settings.SECRET_KEY.encode("utf-8"))
    protected_blob = DATA_BLOB()

    result = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(plain_blob),
        None,
        ctypes.byref(entropy_blob) if entropy_buffer is not None else None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(protected_blob),
    )
    if not result:
        raise RuntimeError("Could not encrypt the client secret.")

    try:
        return base64.b64encode(read_blob(protected_blob)).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(protected_blob.pbData)
        del plain_buffer
        del entropy_buffer


def encrypt_client_passwords(apps, schema_editor):
    Client = apps.get_model("platform_admin", "Client")

    for client in Client.objects.exclude(odoo_password="").all():
        client.odoo_password_encrypted = encrypt_secret(client.odoo_password)
        client.odoo_password = ""
        client.save(update_fields=["odoo_password_encrypted", "odoo_password"])


class Migration(migrations.Migration):

    dependencies = [
        ("platform_admin", "0003_client_odoo_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="odoo_password_encrypted",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(encrypt_client_passwords, migrations.RunPython.noop),
    ]
