from datetime import datetime

from .models import DeadlineRow, DeadlineStatus, EducatorReport, LearnerDeadline


def build_educator_report(
    course_id: str, deadlines: list[LearnerDeadline], now: datetime
) -> EducatorReport:
    rows: list[DeadlineRow] = []
    for deadline in deadlines:
        if deadline.completed_at is not None:
            status = DeadlineStatus.COMPLETE
        elif deadline.due_at < now:
            status = DeadlineStatus.OVERDUE
        else:
            status = DeadlineStatus.OPEN
        rows.append(
            DeadlineRow(
                learner_id=deadline.learner_id,
                lesson_id=deadline.lesson_id,
                due_at=deadline.due_at,
                status=status,
            )
        )
    return EducatorReport(
        course_id=course_id,
        generated_at=now,
        rows=rows,
        overdue_count=sum(row.status == DeadlineStatus.OVERDUE for row in rows),
    )

