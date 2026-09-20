"""Domain schemas, data transfer objects, and types."""

from doubtless.domain.chat import (
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
)
from doubtless.domain.retrieval import (
    BookChunk,
    LectureChunk,
    TranscriptSegment,
)
from doubtless.domain.study import (
    ChaptersPayload,
    Flashcard,
    FlashcardsPayload,
    QuizPayload,
    QuizQuestion,
    VideoChapter,
    VideoChaptersResponse,
    VideoFlashcardsResponse,
    VideoNotes,
    VideoNotesPayload,
    VideoNotesResponse,
    VideoQuizResponse,
)
from doubtless.domain.system import (
    HealthResponse,
)
from doubtless.domain.video import (
    UploadAcceptedResponse,
    UploadConfigResponse,
    VideoDeleteResponse,
    VideoItemResponse,
    VideoRecord,
    VideoStatusResponse,
    VideoStatusState,
)

__all__ = [
    "BookChunk",
    "ChatHistoryResponse",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChaptersPayload",
    "Flashcard",
    "FlashcardsPayload",
    "HealthResponse",
    "LectureChunk",
    "MessageRole",
    "QuizPayload",
    "QuizQuestion",
    "TranscriptSegment",
    "UploadAcceptedResponse",
    "UploadConfigResponse",
    "VideoChapter",
    "VideoChaptersResponse",
    "VideoDeleteResponse",
    "VideoFlashcardsResponse",
    "VideoItemResponse",
    "VideoNotes",
    "VideoNotesPayload",
    "VideoNotesResponse",
    "VideoQuizResponse",
    "VideoRecord",
    "VideoStatusResponse",
    "VideoStatusState",
]
