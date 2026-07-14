from app.services.discord import deserialize_message, serialize_message


def test_embed_payload_round_trips_through_notification_queue_format():
    payload = {
        "embeds": [{"title": "📊 在席日報 · 2026-05-30", "color": 3447003}]
    }
    assert deserialize_message(serialize_message(payload)) == payload


def test_legacy_plain_text_notification_stays_plain_text():
    message = "📖 書桌前時段結束\n09:00 → 09:45（45m）"
    assert deserialize_message(serialize_message(message)) == message
