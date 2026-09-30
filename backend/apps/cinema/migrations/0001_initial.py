from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="Channel", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=160)), ("chat_id", models.BigIntegerField(unique=True, help_text="Telegram numeric chat ID, e.g. -1001234567890")),
            ("join_url", models.URLField(help_text="Public t.me URL or private invite link", max_length=500)),
            ("username", models.CharField(blank=True, help_text="Public channel username without @; leave blank for private", max_length=60)),
            ("active", models.BooleanField(default=True)),
            ("require_post_clicks", models.BooleanField(default=True, help_text="Ask users to open the last five posts observed after the bot became admin")),
        ]),
        migrations.CreateModel(name="Film", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=180)),
            ("slug", models.CharField(max_length=48, unique=True, validators=[django.core.validators.RegexValidator(r"^[a-z0-9][a-z0-9_-]{0,47}$", "Use 1-48 lowercase ASCII letters, numbers, _ or -")])),
            ("description", models.TextField(blank=True)), ("active", models.BooleanField(default=True)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("required_channels", models.ManyToManyField(blank=True, help_text="If empty, all active channels are required", related_name="films", to="cinema.channel")),
        ]),
        migrations.CreateModel(name="BotUser", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("telegram_id", models.BigIntegerField(unique=True)),
            ("language", models.CharField(choices=[("fa", "فارسی"), ("en", "English")], default="fa", max_length=2)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("last_film", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="last_users", to="cinema.film")),
        ]),
        migrations.CreateModel(name="InstagramTask", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=160)),
            ("url", models.URLField(max_length=500, validators=[django.core.validators.URLValidator(schemes=["https"])])),
            ("active", models.BooleanField(default=True)),
            ("films", models.ManyToManyField(blank=True, help_text="If empty, required for every film", related_name="instagram_tasks", to="cinema.film")),
        ]),
        migrations.CreateModel(name="ChannelPost", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("message_id", models.BigIntegerField()), ("posted_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="posts", to="cinema.channel")),
        ], options={"ordering": ["-message_id"]}),
        migrations.CreateModel(name="MediaSource", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("source_chat_id", models.BigIntegerField()), ("source_message_id", models.BigIntegerField()),
            ("media_type", models.CharField(choices=[("video", "Video"), ("document", "Document"), ("animation", "Animation")], max_length=12)),
            ("caption", models.CharField(blank=True, max_length=240)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
        ]),
        migrations.CreateModel(name="FilmAsset", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("position", models.PositiveIntegerField(default=0)),
            ("film", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assets", to="cinema.film")),
            ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="film_assets", to="cinema.mediasource")),
        ], options={"ordering": ["position", "pk"]}),
        migrations.CreateModel(name="LinkVisit", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("film", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cinema.film")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cinema.botuser")),
            ("post", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="cinema.channelpost")),
            ("instagram_task", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="cinema.instagramtask")),
        ]),
        migrations.CreateModel(name="Delivery", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("complete", models.BooleanField(default=False)), ("error", models.CharField(blank=True, max_length=300)),
            ("film", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cinema.film")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cinema.botuser")),
        ]),
        migrations.CreateModel(name="DeliveredMessage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("chat_id", models.BigIntegerField()), ("message_id", models.BigIntegerField()),
            ("expires_at", models.DateTimeField()), ("deleted_at", models.DateTimeField(blank=True, null=True)),
            ("attempts", models.PositiveSmallIntegerField(default=0)),
            ("next_attempt_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("delivery", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="cinema.delivery")),
        ]),
        migrations.CreateModel(name="ProcessedUpdate", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("update_id", models.BigIntegerField(unique=True)),
            ("processed_at", models.DateTimeField(default=django.utils.timezone.now)),
        ]),
        migrations.AddConstraint(model_name="channelpost", constraint=models.UniqueConstraint(fields=("channel", "message_id"), name="unique_channel_message")),
        migrations.AddConstraint(model_name="mediasource", constraint=models.UniqueConstraint(fields=("source_chat_id", "source_message_id"), name="unique_media_source")),
        migrations.AddConstraint(model_name="filmasset", constraint=models.UniqueConstraint(fields=("film", "source"), name="unique_film_asset")),
        migrations.AddConstraint(model_name="linkvisit", constraint=models.UniqueConstraint(fields=("user", "film", "post"), name="unique_post_visit")),
        migrations.AddConstraint(model_name="linkvisit", constraint=models.UniqueConstraint(fields=("user", "film", "instagram_task"), name="unique_instagram_visit")),
        migrations.AddIndex(model_name="deliveredmessage", index=models.Index(fields=["deleted_at", "next_attempt_at"], name="cleanup_due_index")),
        migrations.AddConstraint(model_name="deliveredmessage", constraint=models.UniqueConstraint(fields=("chat_id", "message_id"), name="unique_delivered_msg")),
    ]
