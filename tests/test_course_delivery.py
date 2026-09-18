from datetime import datetime, timedelta, timezone

from course_domain_service.course_delivery import build_educator_report
from course_domain_service.models import DeadlineStatus, LearnerDeadline


def test_report_marks_only_unfinished_past_deadlines_overdue() -> None:
    now = datetime(2026, 9, 13, 9, 0, tzinfo=timezone.utc)
    report = build_educator_report(
        "editing-101",
        [
            LearnerDeadline(
                learner_id="ana", lesson_id="rough-cut", due_at=now - timedelta(days=1)
            ),
            LearnerDeadline(
                learner_id="bo",
                lesson_id="rough-cut",
                due_at=now - timedelta(days=1),
                completed_at=now - timedelta(days=2),
            ),
            LearnerDeadline(
                learner_id="cy", lesson_id="sound-mix", due_at=now + timedelta(days=1)
            ),
        ],
        now,
    )

    assert [row.status for row in report.rows] == [
        DeadlineStatus.OVERDUE,
        DeadlineStatus.COMPLETE,
        DeadlineStatus.OPEN,
    ]
    assert report.overdue_count == 1

