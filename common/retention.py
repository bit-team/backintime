# SPDX-FileCopyrightText: © 2026 Back In Time Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pure retention engine calculating keep sets and deletion lists for snapshots (issue #1945)."""
from dataclasses import dataclass
import datetime
from typing import Any, Sequence, TypeVar


@dataclass(frozen=True)
class SnapshotRecord:
    """Lightweight immutable representation of a snapshot for retention calculation."""
    sid: str
    date: datetime.datetime | datetime.date
    failed: bool = False
    name: str | None = None


@dataclass(frozen=True)
class RetentionPolicy:
    """Configuration for smart removal retention intervals."""
    keep_all_days: int = 2
    keep_one_per_day: int = 7
    keep_one_per_week: int = 4
    keep_one_per_month: int = 24
    keep_one_per_year: int | bool = True
    keep_named: bool = True


T = TypeVar('T')


def get_snapshot_date(item: Any) -> datetime.date:
    """Extract datetime.date from a snapshot record, SID, datetime, or date."""
    if isinstance(item, datetime.date) and not isinstance(item, datetime.datetime):
        return item
    if isinstance(item, datetime.datetime):
        return item.date()
    if hasattr(item, 'date'):
        d = item.date
        if isinstance(d, datetime.datetime):
            return d.date()
        if isinstance(d, datetime.date):
            return d
    raise TypeError(f"Cannot extract date from {item!r}")


def is_snapshot_failed(item: Any) -> bool:
    """Check if snapshot has failed flag."""
    return bool(getattr(item, 'failed', False))


def get_snapshot_name(item: Any) -> str | None:
    """Retrieve custom user label/name of snapshot, if present."""
    name = getattr(item, 'name', None)
    return str(name) if name else None


def inc_month(d: datetime.date) -> datetime.date:
    """Return the 1st day of the next month."""
    year = d.year + 1 if d.month == 12 else d.year
    month = 1 if d.month == 12 else d.month + 1
    return datetime.date(year, month, 1)


def dec_month(d: datetime.date) -> datetime.date:
    """Return the 1st day of the previous month."""
    year = d.year - 1 if d.month == 1 else d.year
    month = 12 if d.month == 1 else d.month - 1
    return datetime.date(year, month, 1)


def keep_all_in_interval(
    snapshots: Sequence[T],
    min_date: datetime.date,
    max_date: datetime.date
) -> set[T]:
    """Return all snapshots whose date falls into [min_date, max_date)."""
    return {
        s for s in snapshots
        if min_date <= get_snapshot_date(s) < max_date
    }


def keep_first_in_interval(
    snapshots: Sequence[T],
    min_date: datetime.date,
    max_date: datetime.date,
    keep_healthy: bool = True
) -> set[T]:
    """Find the first (youngest) snapshot in [min_date, max_date).

    If ``keep_healthy`` is True, prefers the first non-failed snapshot.
    If all snapshots in the range failed, falls back to the first available snapshot.
    """
    for s in snapshots:
        s_date = get_snapshot_date(s)
        if min_date <= s_date < max_date:
            if keep_healthy and is_snapshot_failed(s):
                continue
            return {s}

    if keep_healthy:
        return keep_first_in_interval(snapshots, min_date, max_date, keep_healthy=False)

    return set()


def calculate_retention(
    snapshots: Sequence[T],
    policy: RetentionPolicy,
    now: datetime.date | None = None
) -> tuple[set[T], list[T]]:
    """Calculate the set of snapshots to keep and the list of snapshots to delete.

    Args:
        snapshots: Sequence of snapshot items ordered youngest (newest) first.
        policy: RetentionPolicy specifying retention windows.
        now: Reference date (defaults to today).

    Returns:
        tuple[set[T], list[T]]: (keep_set, to_delete_list)
    """
    if not snapshots:
        return set(), []

    if len(snapshots) <= 1:
        return set(snapshots), []

    if now is None:
        now = datetime.date.today()

    # Always keep the youngest (newest) snapshot
    keep: set[T] = {snapshots[0]}

    # 1. Keep all snapshots for the last keep_all_days
    if policy.keep_all_days > 0:
        min_d = now - datetime.timedelta(days=policy.keep_all_days - 1)
        max_d = now + datetime.timedelta(days=1)
        keep |= keep_all_in_interval(snapshots, min_d, max_d)

    # 2. Keep one snapshot per day for the last keep_one_per_day days
    if policy.keep_one_per_day > 0:
        d = now
        for _ in range(policy.keep_one_per_day):
            keep |= keep_first_in_interval(snapshots, d, d + datetime.timedelta(days=1), keep_healthy=True)
            d -= datetime.timedelta(days=1)

    # 3. Keep one snapshot per week for the last keep_one_per_week weeks (starting Monday)
    if policy.keep_one_per_week > 0:
        d = now - datetime.timedelta(days=now.weekday())
        for _ in range(policy.keep_one_per_week):
            keep |= keep_first_in_interval(snapshots, d, d + datetime.timedelta(days=7), keep_healthy=True)
            d -= datetime.timedelta(days=7)

    # 4. Keep one snapshot per month for the last keep_one_per_month months
    if policy.keep_one_per_month > 0:
        d1 = datetime.date(now.year, now.month, 1)
        d2 = inc_month(d1)
        for _ in range(policy.keep_one_per_month):
            keep |= keep_first_in_interval(snapshots, d1, d2, keep_healthy=True)
            d2 = d1
            d1 = dec_month(d1)

    # 5. Keep one snapshot per year
    if policy.keep_one_per_year is True:
        oldest_year = get_snapshot_date(snapshots[-1]).year
        for year in range(oldest_year, now.year + 1):
            keep |= keep_first_in_interval(
                snapshots,
                datetime.date(year, 1, 1),
                datetime.date(year + 1, 1, 1),
                keep_healthy=True
            )
    elif isinstance(policy.keep_one_per_year, int) and policy.keep_one_per_year > 0:
        oldest_year = get_snapshot_date(snapshots[-1]).year
        start_year = max(now.year - policy.keep_one_per_year + 1, oldest_year)
        for year in range(start_year, now.year + 1):
            keep |= keep_first_in_interval(
                snapshots,
                datetime.date(year, 1, 1),
                datetime.date(year + 1, 1, 1),
                keep_healthy=True
            )

    # Build deletion list (preserve original ordering)
    to_delete = []
    for s in snapshots:
        if s in keep:
            continue
        if policy.keep_named and get_snapshot_name(s):
            continue
        to_delete.append(s)

    return keep, to_delete
