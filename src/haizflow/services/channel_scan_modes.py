"""How far a channel scan reads, and which of the scanned videos it keeps.

A channel is listed newest first, so "what is new" is a prefix of the listing.
The scan stops as soon as the chosen mode is satisfied instead of reading a fixed
number of posts. Pinned posts are exempt from the date/known-run logic because
they sit at the top of a profile whatever their age.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable

from haizflow.schemas.channel_import import ChannelImportRequest, ChannelVideoCandidate

HARD_SCAN_CAP = 1000


def normalize_date(value: str) -> str:
    """'2026-07-15', '2026/07/15' or '20260715' -> '20260715'; '' when not a date."""
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) == 8 else ""


def date_error(request: ChannelImportRequest) -> str:
    if request.scan_mode != "range":
        return ""
    start, end = normalize_date(request.date_from), normalize_date(request.date_to)
    if request.date_from and not start or request.date_to and not end:
        return "Ngày không hợp lệ. Dùng dạng 2026-07-15."
    if not start and not end:
        return "Hãy nhập ít nhất một ngày (từ ngày hoặc đến ngày)."
    if start and end and start > end:
        return "Ngày bắt đầu phải trước ngày kết thúc."
    return ""


def scan_budget(request: ChannelImportRequest) -> int:
    """How many raw posts a scan may read at most (0 means the caller's default)."""
    if request.ranking == "popular":
        return request.scan_scope
    return HARD_SCAN_CAP        # the stop rule ends the scan early; this is only the ceiling


def _row_candidate(row) -> ChannelVideoCandidate:
    return row if isinstance(row, ChannelVideoCandidate) else ChannelVideoCandidate.model_validate(row)


def make_stop(
    request: ChannelImportRequest,
    is_known: Callable[[ChannelVideoCandidate], bool],
    passes: Callable[[ChannelVideoCandidate], bool] = lambda candidate: True,
) -> Callable[[Iterable], bool] | None:
    """A predicate over the rows read so far; True means 'enough, stop reading'."""
    if request.ranking == "popular" or request.scan_mode == "all":
        return None
    parsed: dict[str, ChannelVideoCandidate] = {}
    start = normalize_date(request.date_from)

    def stop(rows: Iterable) -> bool:
        items = []
        for row in rows:
            key = str(row["remote_video_id"] if isinstance(row, dict) else row.remote_video_id)
            if key not in parsed:
                parsed[key] = _row_candidate(row)
            items.append(parsed[key])
        if request.scan_mode == "limit":
            return sum(1 for item in items if passes(item) and not is_known(item)) >= request.limit
        if request.scan_mode == "new":
            run = 0
            for item in reversed(items):
                if item.pinned:
                    continue
                if is_known(item):
                    run += 1
                    continue
                break
            return run >= request.stop_after_known
        if request.scan_mode == "range" and start:
            ordinary = [item for item in items if not item.pinned and item.published_at]
            return bool(ordinary) and ordinary[-1].published_at < start
        return False

    return stop


def select(
    request: ChannelImportRequest,
    candidates: list[ChannelVideoCandidate],
) -> list[ChannelVideoCandidate]:
    """Trim the scanned list to what the mode asks for. Duplicates are already marked."""
    if request.ranking == "popular":
        return candidates[: request.limit]
    mode = request.scan_mode
    if mode == "all":
        return candidates
    if mode == "range":
        start, end = normalize_date(request.date_from), normalize_date(request.date_to)
        return [
            item for item in candidates
            if not item.published_at
            or ((not start or item.published_at >= start) and (not end or item.published_at <= end))
        ]
    if mode == "new":
        keep = [index for index, item in enumerate(candidates) if not item.duplicate]
        return candidates[: keep[-1] + 1] if keep else []
    # limit: stop once the Nth video that is not downloaded yet has been listed
    result, fresh = [], 0
    for item in candidates:
        result.append(item)
        if not item.duplicate:
            fresh += 1
            if fresh >= request.limit:
                break
    return result
