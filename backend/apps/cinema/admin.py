from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from backend.apps.cinema.adapters.bot_credentials import token_for
from backend.apps.cinema.logic.assignment_usecase import AssignFilmBotUsecase
from backend.apps.cinema.logic.publish_usecase import PublishFilmUsecase
from backend.apps.cinema.models import (
    BotAccount, BotUser, Channel, DeliveredMessage, Delivery, Film, FilmAsset,
    InstagramTask, LinkVisit, MediaSource, ProcessedUpdate,
)


@admin.register(BotAccount)
class BotAccountAdmin(admin.ModelAdmin):
    list_display = ["key", "username", "active", "has_token", "created_at"]
    list_filter = ["active"]
    search_fields = ["key", "username"]

    @admin.display(boolean=True, description="Environment token configured")
    def has_token(self, obj):
        try:
            token_for(obj)
            return True
        except RuntimeError:
            return False


class FilmAssetInline(admin.TabularInline):
    model = FilmAsset
    extra = 1
    autocomplete_fields = ["source"]


class FilmAdminForm(forms.ModelForm):
    class Meta:
        model = Film
        fields = "__all__"

    def clean(self):
        data = super().clean()
        if not data.get("channel"):
            self.add_error("channel", "Choose one dedicated channel for this film")
        bot = data.get("bot")
        if self.instance.pk and self.instance.bot_id and (not bot or self.instance.bot_id != bot.pk):
            self.add_error("bot", "Bot assignment is fixed after creation; create a new film and link to reassign")
        if bot and not bot.active:
            self.add_error("bot", "Selected bot is inactive")
        if bot:
            try:
                token_for(bot)
            except RuntimeError as exc:
                self.add_error("bot", str(exc))
        if not bot and not (self.instance.pk and self.instance.bot_id):
            try:
                AssignFilmBotUsecase().choose()
            except ValueError as exc:
                self.add_error("bot", str(exc))
        return data


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    form = FilmAdminForm
    list_display = ["title", "slug", "bot", "channel", "active", "link"]
    list_filter = ["bot", "active"]
    search_fields = ["title", "slug"]
    autocomplete_fields = ["bot", "channel"]
    filter_horizontal = ["required_channels"]
    inlines = [FilmAssetInline]
    readonly_fields = ["link"]
    actions = ["publish_selected"]

    def save_model(self, request, obj, form, change):
        if obj.bot_id is None:
            obj.bot = AssignFilmBotUsecase().choose()  # once at creation, not random on each click
        obj.full_clean(exclude=["required_channels"])
        super().save_model(request, obj, form, change)

    @admin.display(description="Film-specific assigned-bot link")
    def link(self, obj):
        if not obj.pk or not obj.bot_id:
            return "Save the film to assign a bot and create its link"
        url = obj.deep_link()
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, url)

    @admin.action(description="Publish selected films in the central channel")
    def publish_selected(self, request, queryset):
        usecase = PublishFilmUsecase()
        for film in queryset.select_related("bot", "channel"):
            try:
                usecase.execute(film)
            except Exception as exc:
                self.message_user(request, f"Film #{film.pk}: {exc}", level=messages.ERROR)
            else:
                self.message_user(request, f"Film #{film.pk}: published", level=messages.SUCCESS)


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "chat_id", "is_central", "active"]
    list_filter = ["is_central", "active"]
    search_fields = ["name", "username", "chat_id"]


@admin.register(MediaSource)
class MediaSourceAdmin(admin.ModelAdmin):
    list_display = ["id", "bot", "media_type", "source_chat_id", "source_message_id", "caption"]
    search_fields = ["caption", "source_message_id"]


@admin.register(InstagramTask)
class InstagramTaskAdmin(admin.ModelAdmin):
    list_display = ["name", "url", "active"]
    filter_horizontal = ["films"]


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ["telegram_id", "language", "last_film", "created_at"]
    search_fields = ["telegram_id"]


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ["id", "bot", "user", "film", "created_at", "complete", "error"]
    readonly_fields = ["bot", "user", "film", "created_at", "complete", "error"]

    def has_add_permission(self, request):
        return False


@admin.register(DeliveredMessage)
class DeliveredMessageAdmin(admin.ModelAdmin):
    list_display = ["bot", "chat_id", "message_id", "expires_at", "deleted_at", "attempts"]
    readonly_fields = ["bot", "delivery", "chat_id", "message_id", "expires_at", "deleted_at", "attempts", "next_attempt_at"]

    def has_add_permission(self, request):
        return False


@admin.register(LinkVisit)
class LinkVisitAdmin(admin.ModelAdmin):
    list_display = ["user", "film", "post", "instagram_task", "created_at"]
    readonly_fields = ["user", "film", "post", "instagram_task", "created_at"]

    def has_add_permission(self, request):
        return False


@admin.register(ProcessedUpdate)
class ProcessedUpdateAdmin(admin.ModelAdmin):
    list_display = ["bot", "update_id", "processed_at"]
    readonly_fields = ["bot", "update_id", "processed_at"]

    def has_add_permission(self, request):
        return False
