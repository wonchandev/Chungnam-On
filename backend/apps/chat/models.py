from django.conf import settings
from django.db import models


class ChatRoom(models.Model):
    """1:1 채팅방. 공고 문의(job 지정) 또는 친구와의 직접 대화(job=None)."""

    job = models.ForeignKey("jobs.JobPost", null=True, blank=True, on_delete=models.SET_NULL, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]


class ChatParticipant(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_participations")
    language = models.CharField(max_length=10, help_text="이 방에서 사용자가 읽고 쓰는 언어 (번역 언어쌍 설정)")
    last_read_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True, help_text="나간 시각. 상대가 새 메시지를 보내면 다시 보임")

    class Meta:
        unique_together = ("room", "user")


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    text = models.TextField(max_length=2000, blank=True)
    image = models.ImageField(upload_to="chat/", null=True, blank=True)
    source_lang = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["id"]


class MessageTranslation(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="translations")
    lang = models.CharField(max_length=10)
    text = models.TextField()

    class Meta:
        unique_together = ("message", "lang")



class QuickReply(models.Model):
    """채팅 추천 단어/빠른 문장 (한국어 원문, 요청 언어로 번역해 제공)"""

    text_ko = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
