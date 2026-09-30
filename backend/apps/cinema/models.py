from django.conf import settings
from django.core.validators import RegexValidator, URLValidator
from django.db import models
from django.utils import timezone

slug_validator = RegexValidator(r"^[a-z0-9][a-z0-9_-]{0,47}$", "Use 1-48 lowercase ASCII letters, numbers, _ or -")


class BotAccount(models.Model):
    """Public registry only. Secrets live in BOT_TOKEN_<KEY> environment entries."""
    key = models.CharField(max_length=32, unique=True,
                           validators=[RegexValidator(r"^[a-z][a-z0-9_]{0,31}$",
                                                      "Use lowercase letters, digits and underscores")],
                           help_text="Used in BOT_TOKEN_<KEY_UPPER> environment variable")
    username = models.CharField(max_length=60, unique=True, help_text="Bot username without @")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"@{self.username} ({self.key})"


class BotUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    language = models.CharField(max_length=2, default="fa", choices=[("fa", "فارسی"), ("en", "English")])
    last_film = models.ForeignKey("Film", null=True, blank=True, on_delete=models.SET_NULL, related_name="last_users")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.telegram_id)


class Channel(models.Model):
    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.is_central and Channel.objects.filter(is_central=True).exclude(pk=self.pk).exists():
            raise ValidationError("Only one central channel is supported")

    name = models.CharField(max_length=160)
    chat_id = models.BigIntegerField(unique=True, help_text="Telegram numeric chat ID, e.g. -1001234567890")
    join_url = models.URLField(max_length=500, help_text="Public t.me URL or private invite link")
    username = models.CharField(max_length=60, blank=True, help_text="Public channel username without @; leave blank for private")
    active = models.BooleanField(default=True)
    is_central = models.BooleanField(default=False, help_text="Mark the main announcement channel; only one may be central")
    require_post_clicks = models.BooleanField(default=False, help_text="Legacy field: post-click checks are disabled and this value is ignored")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["is_central"], condition=models.Q(is_central=True),
                                                name="unique_central_channel")]

    def __str__(self):
        return self.name


class Film(models.Model):
    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.channel_id and self.channel.is_central:
            raise ValidationError("A dedicated film channel cannot be the central channel")
        if self.channel_id and not self.channel.active:
            raise ValidationError("The dedicated film channel must be active")

    title = models.CharField(max_length=180)
    slug = models.CharField(max_length=48, unique=True, validators=[slug_validator])
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    bot = models.ForeignKey(BotAccount, on_delete=models.PROTECT, null=True, blank=True,
                            related_name="films", help_text="Select a bot; leave empty to assign one randomly on save")
    channel = models.OneToOneField(Channel, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="dedicated_film", help_text="One dedicated channel per film")
    required_channels = models.ManyToManyField(Channel, blank=True, related_name="films",
                                               help_text="Optional additional channels; central and dedicated channels are always required")
    created_at = models.DateTimeField(default=timezone.now)

    def deep_link(self):
        from backend.apps.cinema.vo.callbacks import start_parameter
        username = self.bot.username if self.bot_id else settings.BOT_USERNAME
        if not username:
            raise ValueError("A bot must be assigned before generating the link")
        return f"https://t.me/{username}?start={start_parameter(self.slug)}"

    def __str__(self):
        return self.title


class InstagramTask(models.Model):
    name = models.CharField(max_length=160)
    url = models.URLField(max_length=500, validators=[URLValidator(schemes=["https"])])
    active = models.BooleanField(default=True)
    films = models.ManyToManyField(Film, blank=True, related_name="instagram_tasks", help_text="If empty, required for every film")

    def __str__(self):
        return self.name


class ChannelPost(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="posts")
    message_id = models.BigIntegerField()
    posted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["channel", "message_id"], name="unique_channel_message")]
        ordering = ["-message_id"]

    @property
    def public_url(self):
        if self.channel.username:
            return f"https://t.me/{self.channel.username.lstrip('@')}/{self.message_id}"
        raw = str(self.channel.chat_id)
        if not raw.startswith("-100"):
            raise ValueError("Private channels require a -100... chat ID")
        return f"https://t.me/c/{raw[4:]}/{self.message_id}"

    def __str__(self):
        return f"{self.channel}: {self.message_id}"


class MediaSource(models.Model):
    bot = models.ForeignKey(BotAccount, null=True, blank=True, on_delete=models.PROTECT,
                            help_text="Owner of media sent directly to a bot; blank for shared channel media")
    source_chat_id = models.BigIntegerField()
    source_message_id = models.BigIntegerField()
    media_type = models.CharField(max_length=12, choices=[("video", "Video"), ("document", "Document"), ("animation", "Animation")])
    caption = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source_chat_id", "source_message_id"],
                                    condition=models.Q(bot__isnull=True), name="unique_shared_media_source"),
            models.UniqueConstraint(fields=["bot", "source_chat_id", "source_message_id"],
                                    condition=models.Q(bot__isnull=False), name="unique_bot_media_source"),
        ]

    def __str__(self):
        return f"{self.media_type} {self.source_chat_id}:{self.source_message_id} {self.caption[:40]}"


class FilmAsset(models.Model):
    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if not self.film_id or not self.source_id:
            return
        film, source = self.film, self.source
        if source.bot_id and film.bot_id != source.bot_id:
            raise ValidationError("This source was uploaded to another bot. Use the shared storage channel.")
        if film.bot_id and not source.bot_id and source.source_chat_id not in (
            settings.STORAGE_CHAT_ID, film.channel.chat_id if film.channel_id else None
        ):
            raise ValidationError("Source must come from this film channel or the shared storage channel.")

    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name="assets")
    source = models.ForeignKey(MediaSource, on_delete=models.PROTECT, related_name="film_assets")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [models.UniqueConstraint(fields=["film", "source"], name="unique_film_asset")]

    def __str__(self):
        return f"{self.film} / {self.source}"


class LinkVisit(models.Model):
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    post = models.ForeignKey(ChannelPost, null=True, blank=True, on_delete=models.CASCADE)
    instagram_task = models.ForeignKey(InstagramTask, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "film", "post"], name="unique_post_visit"),
            models.UniqueConstraint(fields=["user", "film", "instagram_task"], name="unique_instagram_visit"),
        ]


class Delivery(models.Model):
    bot = models.ForeignKey(BotAccount, on_delete=models.PROTECT, null=True, blank=True)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    complete = models.BooleanField(default=False)
    error = models.CharField(max_length=300, blank=True)


class DeliveredMessage(models.Model):
    bot = models.ForeignKey(BotAccount, on_delete=models.PROTECT, null=True, blank=True)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="messages")
    chat_id = models.BigIntegerField()
    message_id = models.BigIntegerField()
    expires_at = models.DateTimeField()
    deleted_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["deleted_at", "next_attempt_at"], name="cleanup_due_index")]
        constraints = [models.UniqueConstraint(fields=["bot", "chat_id", "message_id"], name="unique_bot_delivered_msg")]


class ProcessedUpdate(models.Model):
    bot = models.ForeignKey(BotAccount, on_delete=models.CASCADE, null=True, blank=True)
    update_id = models.BigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["bot", "update_id"], name="unique_bot_update")]

    processed_at = models.DateTimeField(default=timezone.now)
