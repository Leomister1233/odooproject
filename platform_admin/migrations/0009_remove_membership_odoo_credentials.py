from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("platform_admin", "0008_membership_odoo_credentials"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="companymembership",
            name="odoo_username",
        ),
        migrations.RemoveField(
            model_name="companymembership",
            name="odoo_password_encrypted",
        ),
    ]
