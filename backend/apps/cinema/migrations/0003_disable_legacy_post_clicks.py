"""Keep existing channel/post data intact while retiring post-view prerequisites."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("cinema", "0002_multi_bot_and_film_channels")]

    operations = [
        migrations.AlterField(
            model_name="channel", name="require_post_clicks",
            field=models.BooleanField(default=False, help_text="Legacy field: post-click checks are disabled and this value is ignored"),
        ),
    ]
