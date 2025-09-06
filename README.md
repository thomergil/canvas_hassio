# Canvas Home Assistant Integration

Canvas custom integration for Home Assistant, based on [schwartzpub's original integration](https://github.com/schwartzpub) with enhancements including improved API compatibility, reliable data fetching, and homework event automation support.

## Installation

### 0. Prerequisites

- Home Assistant instance
- Canvas Parent account with API access
- Active student enrollments linked to your parent account

### 1. Get Canvas API Token

1. **Log into Canvas Parent** via

   ```
   https://[your-school-district].instructure.com/profile/settings
   ```

2. **Create Token**:

   - Under "Approved Integrations" → **"+ New Access Token"**
   - Enter a **Purpose** (e.g., "Home Assistant")
   - Set **Expiration** (or leave blank for no expiration)
   - **Save the token** - you can't retrieve it later!

### 2. Clone to Home Assistant

```bash
# SSH into your Home Assistant instance, then:
cd /config/custom_components/
git clone https://github.com/thomergil/canvas_hassio.git canvas
```

### 3. Restart Home Assistant

Restart Home Assistant to load the integration.

### 4. Configure Integration

1. **Add Integration**:

   - Go to **Settings** → **Devices & Services** → **Integrations**
   - Click **"+ Add Integration"**
   - Search for **"Canvas"**

2. **Enter Configuration**:
   - **Base URL**: `https://your-school.instructure.com`
   - **API Token**: Your token from step 1

### 5. Verify Sensors

The integration creates these sensor entities:

- `sensor.canvas_students` - Your enrolled children
- `sensor.canvas_courses` - Classes your students are taking
- `sensor.canvas_assignments` - Homework and projects
- `sensor.canvas_submissions` - Completed work and grades
- `sensor.canvas_homework_events` - **NEW**: Tracks homework per student and fires automation events

### 6. Install Canvas Cards (Optional)

For enhanced homework display with smart sorting and visual indicators:

```bash
# SSH into your Home Assistant instance, then:
cd /config/www/
git clone https://github.com/thomergil/homeassistant-cards.git
```

See the [Canvas Cards README](https://github.com/thomergil/homeassistant-cards) for complete installation and configuration instructions.

## Updating Integration

When you update the integration:

1. **Pull latest changes**:

   ```bash
   cd /config/custom_components/canvas/
   git pull
   ```

2. **Restart Home Assistant** to apply changes

## Homework Event Automations

### Events Fired

The integration fires two simple events that include complete student information:

#### `canvas_homework_appeared`
Fired when a new assignment is detected for any student. Use conditions/filters in your automations to target specific students.

#### `canvas_homework_completed`
Fired when a homework assignment is submitted by any student. Use conditions/filters in your automations to target specific students.

### Event Data Structure

All events include comprehensive student information:

**Common Event Data:**
- `assignment_id`: Unique Canvas assignment ID
- `assignment_name`: Name of the assignment
- `course_name`: Name of the course
- `student_id`: Canvas student ID
- `student_name`: Full name of the student
- `student_short_name`: Short/preferred name of the student
- `html_url`: Direct link to the assignment in Canvas
- `timestamp`: When the event was detected

**Additional for `homework_appeared` events:**
- `due_at`: Due date/time (if set)
- `points_possible`: Maximum points for the assignment

**Additional for `homework_completed` events:**
- `submitted_at`: When the assignment was submitted
- `score`: Score received (if graded)
- `grade`: Letter grade (if available)

### Homework Events Sensor

The integration includes a **Canvas Homework Events** sensor (`sensor.canvas_homework_events`) that:
- Tracks assignments per student individually
- Provides attributes showing per-student counts of known and completed assignments
- Shows total assignments across all students
- Updates according to your configured scan interval

#### Sensor Attributes
The sensor provides detailed per-student information in its attributes:
```yaml
total_known_assignments: 12
total_completed_assignments: 8
total_pending_assignments: 4
student_count: 2
students:
  "12345":
    name: "Alice Smith"
    known_assignments: 7
    completed_assignments: 5
    pending_assignments: 2
  "67890":
    name: "Bob Smith"
    known_assignments: 5
    completed_assignments: 3
    pending_assignments: 2
```

## Setting Up Homework Automations

### Generic Notification (All Students)
```yaml
- alias: "New Homework Alert"
  trigger:
    - platform: event
      event_type: canvas_homework_appeared
  action:
    - service: notify.mobile_app_your_phone
      data:
        title: "📚 New Homework for {{ trigger.event.data.student_name }}"
        message: "{{ trigger.event.data.assignment_name }} in {{ trigger.event.data.course_name }}"
```

### Student-Specific Automation (Using Conditions)
```yaml
- alias: "Alice's Homework Alert"
  trigger:
    - platform: event
      event_type: canvas_homework_appeared
  condition:
    - condition: template
      value_template: "{{ trigger.event.data.student_name == 'Alice Smith' }}"
  action:
    - service: light.turn_on
      target:
        entity_id: light.alice_room
      data:
        brightness: 200
        color_temp: 250
```

### Different Actions Per Student
```yaml
- alias: "Per-Student Homework Actions"
  trigger:
    - platform: event
      event_type: canvas_homework_completed
  action:
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ trigger.event.data.student_name == 'Alice Smith' }}"
          sequence:
            - service: notify.mobile_app_mom_phone
              data:
                message: "Alice completed {{ trigger.event.data.assignment_name }}!"
        - conditions:
            - condition: template
              value_template: "{{ trigger.event.data.student_name == 'Bob Smith' }}"
          sequence:
            - service: notify.mobile_app_dad_phone
              data:
                message: "Bob completed {{ trigger.event.data.assignment_name }}!"
```

### Student Filtering Options

You have several ways to filter events for specific students:

#### Option 1: Filter by Student Name (Recommended)
```yaml
condition:
  - condition: template
    value_template: "{{ trigger.event.data.student_name == 'Alice Smith' }}"
```

#### Option 2: Filter by Student ID (if you need exact matching)
```yaml
condition:
  - condition: template
    value_template: "{{ trigger.event.data.student_id == '12345' }}"
```

#### Option 3: Filter by Short Name
```yaml
condition:
  - condition: template
    value_template: "{{ trigger.event.data.student_short_name == 'Alice' }}"
```

### Finding Student Information
Check the sensor attributes at `sensor.canvas_homework_events` to see all students and their details, or create a simple logging automation:

```yaml
- alias: "Log Student Info"
  trigger:
    - platform: event
      event_type: canvas_homework_appeared
  action:
    - service: persistent_notification.create
      data:
        title: "Student Info"
        message: "{{ trigger.event.data.student_name }} (ID: {{ trigger.event.data.student_id }})"
```

## Advanced Automation Ideas

### Example: Homework Due Soon Reminder
```yaml
- alias: "Canvas - Homework Due Soon"
  description: "Remind about homework due within 24 hours"
  trigger:
    - platform: event
      event_type: canvas_homework_appeared
  condition:
    - condition: template
      value_template: >
        {% if trigger.event.data.due_at %}
          {{ (trigger.event.data.due_at | as_timestamp - now().timestamp()) < 86400 }}
        {% else %}
          false
        {% endif %}
  action:
    - service: notify.notify
      data:
        title: "⚠️ Homework Due Soon!"
        message: >
          {{ trigger.event.data.assignment_name }}
          for {{ trigger.event.data.student_name }}
          in {{ trigger.event.data.course_name }}
          is due within 24 hours!
```

## Using the Home Assistant UI

**These events are designed to work seamlessly with Home Assistant's visual automation builder!**

### Quick Start Guide:
1. **Go to**: Settings → Automations & Scenes → Create Automation
2. **Trigger**: Choose "Event"
3. **Event Type**: Enter `canvas_homework_appeared` or `canvas_homework_completed`
4. **Condition** (optional): Add template condition for specific students:
   ```yaml
   {{ trigger.event.data.student_name == 'Alice Smith' }}
   ```
5. **Actions**: Use any Home Assistant action (notifications, lights, TTS, etc.)

### Available Event Data:
Use these in your action templates:
- `{{ trigger.event.data.student_name }}` - Full student name
- `{{ trigger.event.data.assignment_name }}` - Assignment title
- `{{ trigger.event.data.course_name }}` - Class name
- `{{ trigger.event.data.due_at }}` - Due date (homework_appeared only)
- `{{ trigger.event.data.score }}` - Grade received (homework_completed only)

**No YAML editing required** - the visual automation builder handles everything!

## State Persistence

The integration uses **persistent storage** to remember which assignments it has seen before:

- **Survives Home Assistant restarts** - no duplicate events after restart
- **Stored in `.storage/` directory** - automatically managed by Home Assistant
- **Per-student tracking** - remembers known and completed assignments for each student
- **Automatic recovery** - if storage fails, starts fresh without errors

### What This Means
- ✅ **First install**: Only truly new assignments after installation will trigger events
- ✅ **After restart**: No duplicate notifications for existing assignments
- ✅ **Reliable tracking**: State persists across updates, reboots, and configuration changes
- ⚠️ **Fresh start**: If you delete `.storage/canvas.canvas_homework_state` file, all current assignments will appear "new" on next poll

### Storage Location
The state is stored in your Home Assistant configuration directory:
```
/config/.storage/canvas.canvas_homework_state
```

This file contains JSON data tracking which assignments have been seen and completed per student. You generally shouldn't need to modify this file manually.

## Related

- **Main Project**: [Canvas Parent Integration](https://github.com/thomergil/canvas-parent-integration)
- **Canvas Cards**: [homeassistant-cards](https://github.com/thomergil/homeassistant-cards) - Enhanced UI cards for displaying homework
- **Original Integration**: Based on [schwartzpub/canvas_hassio](https://github.com/schwartzpub/canvas_hassio)
