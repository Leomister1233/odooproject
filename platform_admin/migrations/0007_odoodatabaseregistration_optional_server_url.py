from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform_admin", "0006_alter_client_table_alter_companymembership_table_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="odoodatabaseregistration",
            name="server_url",
            field=models.URLField(blank=True, default=""),
        ),
    ]
