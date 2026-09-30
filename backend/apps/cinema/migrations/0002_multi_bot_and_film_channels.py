from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("cinema", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="BotAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=32, unique=True, validators=[django.core.validators.RegexValidator(r"^[a-z][a-z0-9_]{0,31}$", "Use lowercase letters, digits and underscores")], help_text="Used in BOT_TOKEN_<KEY_UPPER> environment variable")),
                ("username", models.CharField(max_length=60, unique=True, help_text="Bot username without @")),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.AddField(model_name="channel", name="is_central", field=models.BooleanField(default=False, help_text="Mark the main announcement channel; only one may be central")),
        migrations.AddConstraint(model_name="channel", constraint=models.UniqueConstraint(fields=("is_central",), condition=models.Q(is_central=True), name="unique_central_channel")),
        migrations.AddField(model_name="film", name="bot", field=models.ForeignKey(to="cinema.botaccount", on_delete=django.db.models.deletion.PROTECT, related_name="films", blank=True, null=True, help_text="Select a bot; leave empty to assign one randomly on save")),
        migrations.AddField(model_name="film", name="channel", field=models.OneToOneField(to="cinema.channel", on_delete=django.db.models.deletion.PROTECT, related_name="dedicated_film", blank=True, null=True, help_text="One dedicated channel per film")),
        migrations.AlterField(model_name="film", name="required_channels", field=models.ManyToManyField(to="cinema.channel", blank=True, related_name="films", help_text="Optional additional channels; central and dedicated channels are always required")),
        migrations.AddField(model_name="mediasource", name="bot", field=models.ForeignKey(to="cinema.botaccount", on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, help_text="Owner of media sent directly to a bot; blank for shared channel media")),
        migrations.RemoveConstraint(model_name="mediasource", name="unique_media_source"),
        migrations.AddConstraint(model_name="mediasource", constraint=models.UniqueConstraint(fields=("source_chat_id", "source_message_id"), condition=models.Q(bot__isnull=True), name="unique_shared_media_source")),
        migrations.AddConstraint(model_name="mediasource", constraint=models.UniqueConstraint(fields=("bot", "source_chat_id", "source_message_id"), condition=models.Q(bot__isnull=False), name="unique_bot_media_source")),
        migrations.AddField(model_name="delivery", name="bot", field=models.ForeignKey(to="cinema.botaccount", on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
        migrations.AddField(model_name="deliveredmessage", name="bot", field=models.ForeignKey(to="cinema.botaccount", on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
        migrations.RemoveConstraint(model_name="deliveredmessage", name="unique_delivered_msg"),
        migrations.AddConstraint(model_name="deliveredmessage", constraint=models.UniqueConstraint(fields=("bot", "chat_id", "message_id"), name="unique_bot_delivered_msg")),
        migrations.AddField(model_name="processedupdate", name="bot", field=models.ForeignKey(to="cinema.botaccount", on_delete=django.db.models.deletion.CASCADE, null=True, blank=True)),
        migrations.AlterField(model_name="processedupdate", name="update_id", field=models.BigIntegerField()),
        migrations.AddConstraint(model_name="processedupdate", constraint=models.UniqueConstraint(fields=("bot", "update_id"), name="unique_bot_update")),
    ]
