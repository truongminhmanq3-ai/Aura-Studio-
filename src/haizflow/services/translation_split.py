"""Keep a long translation going when the model fumbles one batch.

A video over ~15 minutes is sent as dozens of batches. Sooner or later one comes back a sentence
short, out of order or cut off, and stopping the whole job there made long videos fail every time.
A batch that comes back wrong is split in half and each half is sent again, down to single
sentences, so one awkward sentence no longer sinks the other 23 in its batch.
"""

from __future__ import annotations

from haizflow.services.video_store import log_to_video


class BadReply(RuntimeError):
    """The model answered, but with a short, reordered or malformed batch: a smaller batch usually fixes it."""


def translate_splitting(chunk, request, save, *, video_id: str = "", provider: str = "") -> None:
    """Translate ``chunk`` with ``request(part) -> list[str]``, handing each good part to ``save(part, values)``.

    Network, key and quota errors are not ``BadReply`` and still stop the job at once: splitting
    cannot fix them. A single sentence that still comes back wrong also stops it, naming that sentence.
    """
    try:
        values = request(chunk)
    except BadReply as exc:
        if len(chunk) == 1:
            raise BadReply(f"{exc} (câu {chunk[0][0] + 1})") from None
        middle = len(chunk) // 2
        log_to_video(
            video_id,
            f"{provider}: lô câu {chunk[0][0] + 1}–{chunk[-1][0] + 1} trả về lỗi ({exc}); "
            f"chia đôi rồi dịch lại.",
            component="TRANSLATE", level="WARNING",
        )
        translate_splitting(chunk[:middle], request, save, video_id=video_id, provider=provider)
        translate_splitting(chunk[middle:], request, save, video_id=video_id, provider=provider)
        return
    save(chunk, values)
