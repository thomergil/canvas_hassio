"""Canvas Hub."""
from __future__ import annotations

import logging
import asyncio
import itertools

from canvas_parent_api import Canvas
from canvas_parent_api.models.assignment import Assignment
from canvas_parent_api.models.course import Course
from canvas_parent_api.models.observee import Observee
from canvas_parent_api.models.submission import Submission

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_BASEURI, CONF_SECRET, DEFAULT_SEMAPHORE, DOMAIN, SCAN_INT, CONF_SEMAPHORE

_LOGGER = logging.getLogger(__name__)


class CanvasHub(DataUpdateCoordinator):
    """Canvas Hub definition."""

    config_entry: config_entries.ConfigEntry

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INT)

        self._baseuri = self.config_entry.data[CONF_BASEURI]
        self._secret = self.config_entry.data[CONF_SECRET]
        self._client = Canvas(f"{self._baseuri}",f"{self._secret}")
        self._semaphore = asyncio.Semaphore(self.config_entry.options.get(CONF_SEMAPHORE, DEFAULT_SEMAPHORE))

    async def get_students(self):
        """Get handler for students."""
        return await self._client.observees()

    async def get_courses(self, student_id, sem):
        """Get handler for courses."""
        async with sem:
            return await self._client.courses(student_id)

    async def get_assignments(self, student_id, course_id, sem):
        """Get handler for assignments."""
        async with sem:
            return await self._client.assignments(student_id,course_id)

    async def get_submissions(self, student_id, course_id, sem):
        """Get handler for submissions."""
        async with sem:
            return await self._client.submissions(student_id,course_id)

    async def poll_observees(self) -> list[dict]:
        """Get Canvas Observees (students)."""
        return await self.get_students()

    async def poll_courses(self) -> list[dict]:
        """Get Canvas Courses."""
        courses: list[Course] = []

        observees = await self.get_students()
        for observee in observees:
            courseresp = await self.get_courses(observee.id, self._semaphore)
            courses.extend([Course(course) for course in courseresp])
        return courses

    async def poll_assignments(self) -> list[dict]:
        """Get Canvas Assignments."""
        assignments: list[Assignment] = []
        assignment_tasks = []

        courses = await self.poll_courses()
        for course in courses:
            observee = course.enrollments[0]
            if observee is not None:
                assignment_tasks.append(asyncio.create_task(self.get_assignments(observee.get("user_id", ""), course.id, self._semaphore)))
        assignment_results = await asyncio.gather(*assignment_tasks)
        assignments.extend(
            [Assignment(assignment) for assignment in itertools.chain.from_iterable(assignment_results)]
        )
        return assignments

    async def poll_pending_assignments(self) -> list[dict]:
        """Get only pending (unsubmitted/ungraded) Canvas Assignments."""
        # Get all assignments and submissions
        assignments = await self.poll_assignments()
        submissions = await self.poll_submissions()

        # Create lookup of submitted assignment IDs
        submitted_assignment_ids = set()
        for submission in submissions:
            if hasattr(submission, 'workflow_state') and hasattr(submission, 'assignment_id'):
                workflow_state = getattr(submission, 'workflow_state', None)
                submitted_at = getattr(submission, 'submitted_at', None)

                # Consider assignment submitted if it has been submitted (not just drafted)
                if workflow_state == 'submitted' and submitted_at:
                    assignment_id = str(getattr(submission, 'assignment_id', ''))
                    if assignment_id:
                        submitted_assignment_ids.add(assignment_id)

        # Filter out submitted assignments
        pending_assignments = []
        for assignment in assignments:
            assignment_id = str(getattr(assignment, 'id', ''))
            if assignment_id and assignment_id not in submitted_assignment_ids:
                pending_assignments.append(assignment)

        return pending_assignments

    async def poll_submissions(self) -> list[dict]:
        """Get Canvas Assignments."""
        submissions: list[Submission] = []
        submission_tasks = []

        courses = await self.poll_courses()
        for course in courses:
            observee = course.enrollments[0]
            if observee is not None:
                submission_tasks.append(asyncio.create_task(self.get_submissions(observee.get("user_id", ""), course.id, self._semaphore)))
        submission_results = await asyncio.gather(*submission_tasks)
        submissions.extend(
            [Submission(submission) for submission in itertools.chain.from_iterable(submission_results)]
        )
        return submissions
