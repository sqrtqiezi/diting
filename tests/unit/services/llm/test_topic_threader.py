"""话题线程切分器测试"""

from __future__ import annotations

from diting.services.llm.config import ThreadingConfig
from diting.services.llm.topic_threader import TopicThreader


def test_threader_splits_by_similarity() -> None:
    config = ThreadingConfig(
        enabled=True,
        time_window_minutes=60,
        similarity_threshold=0.8,
        reply_boost=0.1,
    )
    threader = TopicThreader(config, tz=None)

    messages = [
        {"msg_id": "m1", "content": "btc", "chatroom_sender": "alice", "create_time": 1},
        {"msg_id": "m2", "content": "bitcoin", "chatroom_sender": "bob", "create_time": 2},
        {"msg_id": "m3", "content": "ai", "chatroom_sender": "carl", "create_time": 3},
    ]
    message_ids = ["m1", "m2", "m3"]
    embeddings = [
        [1.0, 0.0],
        [0.9, 0.1],
        [0.0, 1.0],
    ]

    batches = threader.split_messages(messages, message_ids, embeddings)

    assert len(batches) == 2
    assert batches[0].message_ids == ["m1", "m2"]
    assert batches[1].message_ids == ["m3"]


def test_threader_respects_time_window() -> None:
    config = ThreadingConfig(
        enabled=True,
        time_window_minutes=1,
        similarity_threshold=0.7,
        reply_boost=0.1,
    )
    threader = TopicThreader(config, tz=None)

    messages = [
        {"msg_id": "m1", "content": "btc", "chatroom_sender": "alice", "create_time": 1},
        {"msg_id": "m2", "content": "btc2", "chatroom_sender": "bob", "create_time": 3600},
    ]
    message_ids = ["m1", "m2"]
    embeddings = [
        [1.0, 0.0],
        [0.99, 0.01],
    ]

    batches = threader.split_messages(messages, message_ids, embeddings)

    assert len(batches) == 2
    assert batches[0].message_ids == ["m1"]
    assert batches[1].message_ids == ["m2"]


def test_threader_reply_boosts_similarity() -> None:
    config = ThreadingConfig(
        enabled=True,
        time_window_minutes=60,
        similarity_threshold=0.75,
        reply_boost=0.2,
    )
    threader = TopicThreader(config, tz=None)

    messages = [
        {"msg_id": "m1", "content": "btc", "chatroom_sender": "alice", "create_time": 1},
        {
            "msg_id": "m2",
            "content": "ok",
            "chatroom_sender": "bob",
            "create_time": 2,
            "refermsg": {"displayname": "alice"},
        },
    ]
    message_ids = ["m1", "m2"]
    embeddings = [
        [1.0, 0.0],
        [0.6, 0.8],
    ]

    batches = threader.split_messages(messages, message_ids, embeddings)

    assert len(batches) == 1
    assert batches[0].message_ids == ["m1", "m2"]
