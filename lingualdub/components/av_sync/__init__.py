"""AV-sync components for Milestone 7."""

try:
    from lingualdub.components.av_sync.dialogue_timing import DialogueTimingComponent
except ImportError:
    DialogueTimingComponent = None  # type: ignore

try:
    from lingualdub.components.av_sync.video_merger import VideoMergerComponent
except ImportError:
    VideoMergerComponent = None  # type: ignore

__all__ = ["DialogueTimingComponent", "VideoMergerComponent"]
