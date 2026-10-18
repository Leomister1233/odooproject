from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform_admin", "0007_odoodatabaseregistration_optional_server_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="companymembership",
            name="odoo_username",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="companymembership",
            name="odoo_password_encrypted",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="odoodatabaseregistration",
            name="username_encrypted",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="odoodatabaseregistration",
            name="password_encrypted",
            field=models.TextField(blank=True, default=""),
        ),
    ]
