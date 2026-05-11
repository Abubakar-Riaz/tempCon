import secrets
from django.db import models
from django.utils import timezone

PUBLIC_ID_BYTES = 12  # 24 char hex


def generate_public_id() -> str:
    return secrets.token_hex(PUBLIC_ID_BYTES)


class PublicIDModel(models.Model):
    public_id = models.CharField(
        max_length=24,
        unique=True,
        db_index=True,
        editable=False,
        default=generate_public_id,
    )

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True