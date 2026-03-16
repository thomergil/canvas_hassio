# Canvas for Home Assistant

Display your children's [Canvas LMS](https://www.instructure.com/canvas) homework on your Home Assistant dashboard, with optional notifications when assignments appear or are completed.

Based on [schwartzpub's original integration](https://github.com/schwartzpub/canvas_hassio) and [canvas_parent_api](https://github.com/schwartzpub/canvas_parent_api).

## Features

- Dashboard card showing upcoming homework per student, sorted by due date
- Sensors for students, courses, assignments, and submissions
- Events for new and completed homework (for automations/notifications)
- Persistent state tracking (survives restarts, no duplicate notifications)
- Polls Canvas every 10 minutes

## Installation

### Step 1: Get a Canvas API Token

1. Log into Canvas as a parent at `https://yourschool.instructure.com`
2. Go to **Account → Settings**
3. Under **Approved Integrations**, click **+ New Access Token**
4. Enter a purpose (e.g., "Home Assistant"), click **Generate Token**
5. **Copy the token immediately** — you cannot retrieve it later

### Step 2: Install the Integration

#### Option A: HACS (recommended)

1. In HACS, click the three dots menu → **Custom repositories**
2. Add `https://github.com/thomergil/canvas_hassio` as type **Integration**
3. Find "Canvas" in HACS and click **Install**
4. Restart Home Assistant (in the terminal: `ha core restart`)

#### Option B: Manual

```bash
cd /config/custom_components/
git clone https://github.com/thomergil/canvas_hassio.git canvas
```

Restart Home Assistant (in the terminal: `ha core restart`).

### Step 3: Configure

1. Go to **Settings → Devices & Services → Integrations**
2. Click **+ Add Integration**, search for **Canvas**
3. Enter your Canvas URL (e.g., `https://yourschool.instructure.com`)
4. Paste your API token
5. Click **Submit**

### Step 4: Add the Dashboard Card

The card is automatically registered when the integration loads. After configuring the integration, hard refresh your browser (Ctrl+Shift+R / Cmd+Shift+R), then:

1. Edit your dashboard
2. Click **+ Add Card**
3. Search for **"Canvas"** — select **Canvas - Homework Card**
4. Configure the options in the UI, or switch to YAML and paste:

```yaml
type: custom:canvas-homework
title: Homework
look_ahead_days: 5
overdue_cutoff_days: 5
course_sort_order: due_date
entities:
  - entity: sensor.canvas_students
  - entity: sensor.canvas_courses
  - entity: sensor.canvas_assignments
  - entity: sensor.canvas_submissions
```

#### Card Options

| Option | Default | Description |
|--------|---------|-------------|
| `title` | `Canvas - Homework` | Card header (set to `""` for no title) |
| `look_ahead_days` | `5` | Days ahead to show |
| `overdue_cutoff_days` | `5` | Days back to show overdue |
| `course_sort_order` | `due_date` | `due_date` or `alphabetical` |

## Sensors

The integration creates five sensors:

| Sensor | Description |
|--------|-------------|
| `sensor.canvas_students` | Your enrolled children |
| `sensor.canvas_courses` | Their courses |
| `sensor.canvas_assignments` | Pending assignments |
| `sensor.canvas_submissions` | Submitted work and grades |
| `sensor.canvas_homework_events` | Per-student assignment tracking |

## Automations

The integration fires two events:

- **`canvas_homework_appeared`** — new assignment detected
- **`canvas_homework_completed`** — assignment submitted

### Example: Notify on New Homework

```yaml
alias: New Homework Alert
trigger:
  - platform: event
    event_type: canvas_homework_appeared
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "New Homework for {{ trigger.event.data.student_name }}"
      message: >
        {{ trigger.event.data.assignment_name }}
        in {{ trigger.event.data.course_name }}
        — due {{ trigger.event.data.due_at }}
```

### Example: Per-Student Notifications

```yaml
alias: Alice's Homework Alert
trigger:
  - platform: event
    event_type: canvas_homework_appeared
condition:
  - condition: template
    value_template: "{{ trigger.event.data.student_name == 'Alice Smith' }}"
action:
  - service: notify.mobile_app_your_phone
    data:
      message: "{{ trigger.event.data.assignment_name }} in {{ trigger.event.data.course_name }}"
```

### Event Data

**`canvas_homework_appeared`:** `student_name`, `student_id`, `student_short_name`, `assignment_name`, `assignment_id`, `course_name`, `due_at`, `points_possible`, `html_url`, `timestamp`

**`canvas_homework_completed`:** all of the above plus `submitted_at`, `score`, `grade`

## Updating

#### HACS
Update through the HACS UI, then restart Home Assistant (`ha core restart`).

#### Manual
```bash
cd /config/custom_components/canvas && git pull
```

Restart Home Assistant (`ha core restart`).

## Troubleshooting

**Sensors show "unavailable":** Check your API token hasn't expired. Go to Canvas → Account → Settings → Approved Integrations.

**Card not showing:** Try a hard refresh in your browser (Ctrl+Shift+R / Cmd+Shift+R). If that doesn't work, restart Home Assistant (`ha core restart`).

**Duplicate notifications after restart:** The integration uses persistent storage in `/config/.storage/canvas.canvas_homework_state`. Delete this file only if you want a fresh start (all current assignments will appear as "new").
