"""Platform for sensor integration."""
from __future__ import annotations

import logging
import json
from datetime import datetime
from typing import Dict, Set, Any

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .const import DOMAIN, SCAN_INT

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = SCAN_INT

# Storage constants
STORAGE_VERSION = 1
STORAGE_KEY = "canvas_homework_state"

@dataclass
class CanvasEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable
    unique_id: str


@dataclass
class CanvasEntityDescription(
    SensorEntityDescription, CanvasEntityDescriptionMixin
):
    """Describes AdGuard Home sensor entity."""

SENSORS: tuple[CanvasEntityDescription, ...] = (
    CanvasEntityDescription(
        key="student",
        name="Canvas Students",
        unique_id="canvas_student",
        value_fn=lambda canvas: canvas.poll_observees()
    ),
    CanvasEntityDescription(
        key="course",
        name="Canvas Courses",
        unique_id="canvas_course",
        value_fn=lambda canvas: canvas.poll_courses()
    ),
    CanvasEntityDescription(
        key="assignment",
        name="Canvas Assignments",
        unique_id="canvas_assignment",
        value_fn=lambda canvas: canvas.poll_assignments()
    ),
    CanvasEntityDescription(
        key="submission",
        name="Canvas Submissions",
        unique_id="canvas_submission",
        value_fn=lambda canvas: canvas.poll_submissions()
    ),
    CanvasEntityDescription(
        key="homework_events",
        name="Canvas Homework Events",
        unique_id="canvas_homework_events",
        value_fn=lambda canvas: canvas.poll_assignments()
    )
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
    ):
    """Set up the sensor platform."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for description in SENSORS:
        if description.key == "homework_events":
            entities.append(CanvasHomeworkEventSensor(description, hub, hass))
        else:
            entities.append(CanvasSensor(description, hub))

    async_add_entities(entities, True)


class CanvasSensor(SensorEntity):
    """Canvas Sensor Definition."""
    entity_description: CanvasEntityDescription

    def __init__(
        self,
        description: CanvasEntityDescription,
        hub
    ) -> None:
        self._hub = hub
        self._attr_name = description.name
        self._attr_unique_id = f"{description.unique_id}"
        self._entity_description = description
        self._attr_canvas_data = {}

    @property
    def extra_state_attributes(self):
        """Add extra attribute with size limits to prevent database issues."""
        if not self._attr_canvas_data:
            return {f"{self._entity_description.key}_count": 0}
        
        # Limit data size to prevent 16KB database limit issues
        data_list = []
        total_size = 0
        max_size = 12000  # Leave some room under 16KB limit
        
        for item in self._attr_canvas_data:
            if item is None:
                continue
                
            try:
                item_dict = item.as_dict() if hasattr(item, 'as_dict') else str(item)
                item_size = len(str(item_dict))
                
                if total_size + item_size > max_size:
                    break
                    
                data_list.append(item_dict)
                total_size += item_size
                
            except Exception as e:
                _LOGGER.debug(f"Error serializing item: {e}")
                continue
        
        return {
            f"{self._entity_description.key}": data_list,
            f"{self._entity_description.key}_count": len(self._attr_canvas_data),
            f"{self._entity_description.key}_truncated": len(data_list) < len(self._attr_canvas_data)
        }

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._attr_canvas_data = await self._entity_description.value_fn(self._hub)
        return


class CanvasHomeworkEventSensor(CanvasSensor):
    """Canvas Homework Event Sensor that fires HA events per student."""

    def __init__(
        self,
        description: CanvasEntityDescription,
        hub,
        hass: HomeAssistant
    ) -> None:
        super().__init__(description, hub)
        self._hass = hass
        self._previous_assignments: Dict[str, Any] = {}
        self._previous_submissions: Dict[str, Any] = {}
        # Track per student: student_id -> set of assignment_ids
        self._known_assignment_ids_per_student: Dict[str, Set[str]] = {}
        self._completed_assignment_ids_per_student: Dict[str, Set[str]] = {}
        self._student_info: Dict[str, Dict[str, Any]] = {}  # Cache student info

        # Set up persistent storage
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{STORAGE_KEY}")
        self._loaded_from_storage = False

    async def async_update(self) -> None:
        """Fetch new state data and fire events for homework changes."""
        try:
            # Load state from storage on first update
            if not self._loaded_from_storage:
                await self._load_state_from_storage()
                self._loaded_from_storage = True

            # Get current data with validation
            current_students = await self._hub.poll_observees() or []
            current_courses = await self._hub.poll_courses() or []
            current_assignments = await self._hub.poll_assignments() or []
            current_submissions = await self._hub.poll_submissions() or []
            
            # Validate API responses
            if not isinstance(current_students, list):
                _LOGGER.warning(f"Invalid students data type: {type(current_students)}")
                current_students = []
            if not isinstance(current_courses, list):
                _LOGGER.warning(f"Invalid courses data type: {type(current_courses)}")
                current_courses = []
            if not isinstance(current_assignments, list):
                _LOGGER.warning(f"Invalid assignments data type: {type(current_assignments)}")
                current_assignments = []
            if not isinstance(current_submissions, list):
                _LOGGER.warning(f"Invalid submissions data type: {type(current_submissions)}")
                current_submissions = []

            # Update student info cache
            await self._update_student_info(current_students)

            # Create assignment to student mapping
            assignment_to_student = await self._create_assignment_student_mapping(current_courses, current_assignments)

            # Group assignments and submissions by student
            assignments_by_student = self._group_by_student(current_assignments, assignment_to_student)
            submissions_by_student = self._group_submissions_by_student(current_submissions, assignment_to_student)

            # Check for new assignments and completed homework per student
            for student_id, assignments in assignments_by_student.items():
                await self._check_new_assignments_for_student(student_id, assignments)
                await self._check_completed_assignments_for_student(student_id, assignments, submissions_by_student.get(student_id, {}))

            # Save state after processing
            await self._save_state_to_storage()

            # Update stored state
            self._attr_canvas_data = current_assignments

        except Exception as e:
            _LOGGER.error(f"Error updating homework events sensor: {e}")

    async def _update_student_info(self, students) -> None:
        """Update cached student information."""
        for student in students:
            student_id = str(getattr(student, 'id', ''))
            if student_id:
                self._student_info[student_id] = {
                    'id': student_id,
                    'name': getattr(student, 'name', f'Student {student_id}'),
                    'short_name': getattr(student, 'short_name', getattr(student, 'name', f'Student {student_id}')),
                    'sortable_name': getattr(student, 'sortable_name', getattr(student, 'name', f'Student {student_id}'))
                }

    async def _create_assignment_student_mapping(self, courses, assignments) -> Dict[str, str]:
        """Create mapping from assignment_id to student_id."""
        assignment_to_student = {}

        # Create course to student mapping first
        course_to_student = {}
        for course in courses:
            if course is None:
                continue
                
            course_id = str(getattr(course, 'id', ''))
            enrollments = getattr(course, 'enrollments', [])
            
            if enrollments and len(enrollments) > 0 and enrollments[0] is not None:
                # Safely handle enrollment data
                enrollment = enrollments[0]
                if isinstance(enrollment, dict):
                    student_id = str(enrollment.get('user_id', ''))
                else:
                    student_id = str(getattr(enrollment, 'user_id', ''))
                
                if course_id and student_id:
                    course_to_student[course_id] = student_id

        # Map assignments to students via courses
        for assignment in assignments:
            assignment_id = str(getattr(assignment, 'id', ''))
            course_id = str(getattr(assignment, 'course_id', ''))
            if assignment_id and course_id in course_to_student:
                assignment_to_student[assignment_id] = course_to_student[course_id]

        return assignment_to_student

    def _group_by_student(self, assignments, assignment_to_student) -> Dict[str, Dict[str, Any]]:
        """Group assignments by student."""
        assignments_by_student = {}
        for assignment in assignments:
            if assignment is None:
                continue
                
            assignment_id = str(getattr(assignment, 'id', ''))
            student_id = assignment_to_student.get(assignment_id)
            if student_id and assignment_id:
                if student_id not in assignments_by_student:
                    assignments_by_student[student_id] = {}
                assignments_by_student[student_id][assignment_id] = assignment
        return assignments_by_student

    def _group_submissions_by_student(self, submissions, assignment_to_student) -> Dict[str, Dict[str, Any]]:
        """Group submissions by student."""
        submissions_by_student = {}
        for submission in submissions:
            assignment_id = str(getattr(submission, 'assignment_id', ''))
            student_id = assignment_to_student.get(assignment_id)
            if student_id:
                if student_id not in submissions_by_student:
                    submissions_by_student[student_id] = {}
                submissions_by_student[student_id][assignment_id] = submission
        return submissions_by_student

    async def _check_new_assignments_for_student(self, student_id: str, assignments: Dict[str, Any]) -> None:
        """Check for new assignments for a specific student and fire events."""
        if student_id not in self._known_assignment_ids_per_student:
            self._known_assignment_ids_per_student[student_id] = set()

        student_info = self._student_info.get(student_id, {})

        for assignment_id, assignment in assignments.items():
            if assignment_id not in self._known_assignment_ids_per_student[student_id] and assignment_id:
                self._known_assignment_ids_per_student[student_id].add(assignment_id)

                # Fire new homework event with student information
                event_data = {
                    "assignment_id": assignment_id,
                    "assignment_name": getattr(assignment, 'name', 'Unknown Assignment'),
                    "course_name": getattr(assignment, 'course_name', 'Unknown Course'),
                    "due_at": getattr(assignment, 'due_at', None),
                    "points_possible": getattr(assignment, 'points_possible', None),
                    "html_url": getattr(assignment, 'html_url', None),
                    "student_id": student_id,
                    "student_name": student_info.get('name', f'Student {student_id}'),
                    "student_short_name": student_info.get('short_name', student_info.get('name', f'Student {student_id}')),
                    "timestamp": datetime.now().isoformat()
                }

                # Fire generic event with student data
                self._hass.bus.async_fire("canvas_homework_appeared", event_data)
                _LOGGER.info(f"New homework appeared for {student_info.get('name', student_id)}: {event_data['assignment_name']} in {event_data['course_name']}")

    async def _check_completed_assignments_for_student(self, student_id: str, assignments: Dict[str, Any], submissions: Dict[str, Any]) -> None:
        """Check for completed assignments for a specific student and fire events."""
        if student_id not in self._completed_assignment_ids_per_student:
            self._completed_assignment_ids_per_student[student_id] = set()

        student_info = self._student_info.get(student_id, {})

        for assignment_id, assignment in assignments.items():
            if assignment_id in submissions and assignment_id not in self._completed_assignment_ids_per_student[student_id]:
                submission = submissions[assignment_id]

                # Check if submission is actually submitted (not just drafted)
                workflow_state = getattr(submission, 'workflow_state', None)
                submitted_at = getattr(submission, 'submitted_at', None)

                if workflow_state == 'submitted' and submitted_at:
                    self._completed_assignment_ids_per_student[student_id].add(assignment_id)

                    # Fire homework completed event with student information
                    event_data = {
                        "assignment_id": assignment_id,
                        "assignment_name": getattr(assignment, 'name', 'Unknown Assignment'),
                        "course_name": getattr(assignment, 'course_name', 'Unknown Course'),
                        "submitted_at": submitted_at,
                        "score": getattr(submission, 'score', None),
                        "grade": getattr(submission, 'grade', None),
                        "html_url": getattr(assignment, 'html_url', None),
                        "student_id": student_id,
                        "student_name": student_info.get('name', f'Student {student_id}'),
                        "student_short_name": student_info.get('short_name', student_info.get('name', f'Student {student_id}')),
                        "timestamp": datetime.now().isoformat()
                    }

                    # Fire generic event with student data
                    self._hass.bus.async_fire("canvas_homework_completed", event_data)
                    _LOGGER.info(f"Homework completed for {student_info.get('name', student_id)}: {event_data['assignment_name']} in {event_data['course_name']}")

    async def _load_state_from_storage(self) -> None:
        """Load the tracking state from persistent storage."""
        try:
            data = await self._store.async_load()
            if data is not None:
                # Convert list back to set for known assignments
                self._known_assignment_ids_per_student = {
                    student_id: set(assignment_ids)
                    for student_id, assignment_ids in data.get('known_assignments', {}).items()
                }
                # Convert list back to set for completed assignments
                self._completed_assignment_ids_per_student = {
                    student_id: set(assignment_ids)
                    for student_id, assignment_ids in data.get('completed_assignments', {}).items()
                }
                # Load student info
                self._student_info = data.get('student_info', {})

                _LOGGER.info(f"Loaded homework state from storage: {len(self._known_assignment_ids_per_student)} students tracked")
            else:
                _LOGGER.info("No previous homework state found, starting fresh")
        except Exception as e:
            _LOGGER.warning(f"Failed to load homework state from storage: {e}")
            # Initialize empty state on load failure
            self._known_assignment_ids_per_student = {}
            self._completed_assignment_ids_per_student = {}
            self._student_info = {}

    async def _save_state_to_storage(self) -> None:
        """Save the tracking state to persistent storage."""
        try:
            # Convert sets to lists for JSON serialization
            data = {
                'known_assignments': {
                    student_id: list(assignment_ids)
                    for student_id, assignment_ids in self._known_assignment_ids_per_student.items()
                },
                'completed_assignments': {
                    student_id: list(assignment_ids)
                    for student_id, assignment_ids in self._completed_assignment_ids_per_student.items()
                },
                'student_info': self._student_info,
                'last_saved': datetime.now().isoformat()
            }
            await self._store.async_save(data)
        except Exception as e:
            _LOGGER.error(f"Failed to save homework state to storage: {e}")

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return len(self._attr_canvas_data) if self._attr_canvas_data else 0

    @property
    def extra_state_attributes(self):
        """Add extra attributes including per-student event counts."""
        base_attrs = super().extra_state_attributes

        # Calculate totals
        total_known = sum(len(assignments) for assignments in self._known_assignment_ids_per_student.values())
        total_completed = sum(len(assignments) for assignments in self._completed_assignment_ids_per_student.values())

        # Per-student breakdown
        students_info = {}
        for student_id, student_info in self._student_info.items():
            known_count = len(self._known_assignment_ids_per_student.get(student_id, set()))
            completed_count = len(self._completed_assignment_ids_per_student.get(student_id, set()))
            students_info[student_id] = {
                "name": student_info.get('name', f'Student {student_id}'),
                "known_assignments": known_count,
                "completed_assignments": completed_count,
                "pending_assignments": known_count - completed_count
            }

        base_attrs.update({
            "total_known_assignments": total_known,
            "total_completed_assignments": total_completed,
            "total_pending_assignments": total_known - total_completed,
            "students": students_info,
            "student_count": len(self._student_info),
            "last_update": datetime.now().isoformat()
        })
        return base_attrs
