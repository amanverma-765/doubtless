"""Domain type aliases and literal enumerations for video processing and chat."""

from typing import Literal

# Lifecycle states of video transcoding and upload pipeline
VideoStatusState = Literal["idle", "uploading", "processing", "ready", "error"]

# Sender roles in doubt-resolution chat threads
MessageRole = Literal["user", "assistant", "system"]
