# Canvas Home Assistant Integration

Canvas custom integration for Home Assistant, based on [schwartzpub's original integration](https://github.com/schwartzpub) with enhancements including improved API compatibility and reliable data fetching.

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

## Related

- **Main Project**: [Canvas Parent Integration](https://github.com/thomergil/canvas-parent-integration)
- **Canvas Cards**: [homeassistant-cards](https://github.com/thomergil/homeassistant-cards) - Enhanced UI cards for displaying homework
- **Original Integration**: Based on [schwartzpub/canvas_hassio](https://github.com/schwartzpub/canvas_hassio)
