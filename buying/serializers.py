# buying/serializers.py

from rest_framework import serializers

from buying.models import BuyingDecision, BuyingDecisionStatus


class BuyingDecisionUpdateSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=BuyingDecisionStatus.values)
    notes = serializers.CharField(required=False, allow_blank=True)


class BuyingDecisionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    buyer = serializers.SerializerMethodField()

    class Meta:
        model = BuyingDecision
        fields = (
            "id",
            "decision",
            "notes",
            "decided_at",
            "buyer",
            "created_at",
            "updated_at",
        )

    def get_buyer(self, obj):
        if not obj.buyer:
            return None

        return {
            "id": obj.buyer.public_id,
            "email": obj.buyer.email,
            "name": obj.buyer.display_name,
        }