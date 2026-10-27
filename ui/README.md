# Streamlit user interface

Each domain can supply its own page without changing the application shell. `app.py` owns navigation, page configuration, and styling. `ui/domain_views.py` is the registration point for domain pages. `ui/dashboard.py` supplies the operational Overview and Pet Care workspace, with editable sample readings, saved results, and filtered history.

## Add a domain page

1. Create `ui/<domain>.py` with a zero-argument render function. Keep input controls and result presentation in this file; call your domain handler to perform the assessment or action.
2. Import that function in `ui/domain_views.py` and add it to `DOMAIN_VIEWS`, preserving the other registrations.
3. Use the domain name exactly as it appears in `ui/dashboard.py`:

   - `Pet Care`
   - `Elderly Safety`
   - `Smart Home Control`
   - `Home Security`
   - `Energy & Comfort`

For example, create `ui/elderly_safety.py`:

```python
import streamlit as st


def render_elderly_safety() -> None:
    st.header("Elderly Safety")
    # Collect inputs, call the domain handler, and display its actual result here.
    st.info("This page is being connected. No monitoring is active yet.")
```

Then extend `ui/domain_views.py`:

```python
from ui.elderly_safety import render_elderly_safety

# Add this entry inside the existing DOMAIN_VIEWS dictionary:
"Elderly Safety": render_elderly_safety,
```

The sidebar and Overview's Home services section will open the registered function automatically. Home services receives the registered domain names from `app.py`, so its availability labels follow the registry. Unregistered domains retain their pending page. Registration alone does not add a domain's readings to Overview metrics or history; coordinate those shared displays with the UI integration owner.

## Keep pages compatible

- Reuse Streamlit controls and the styles applied by `app.py`. Do not call `st.set_page_config()` or inject a replacement theme in a domain page. The interface does not require external images or font downloads.
- Prefix widget keys and session-state entries with your domain, for example `elderly_safety_scenario`, to avoid collisions.
- Put business rules in `domains/`, shared agent orchestration in `agents/`, and device access in `tools/`. Pages should call those interfaces, not duplicate rules or operate devices directly.
- Show the result returned by the handler, including failures. Clearly label sample readings and simulated actions; report notifications or device changes only when the result confirms them.
- Keep API keys in local configuration. Do not place keys in page code, screenshots, or committed files.

## Current integration status

Overview and Pet Care share a working sample-input workspace. Presets initialise the reading; the `pet_value` input lets users change it before running a check. The page creates a sensor event with `simulation.events.make_sensor_event`, calls `domains.pet_care.integration.monitor_pet_workflow`, and displays the saved assessment, shared workflow trace and simulated owner-alert outcome. Saved readings feed the summary metrics and history filters. These are simulated inputs, not live sensor connections.

Smart Home Control is also connected. Its page creates a direct user-goal event, runs the shared coordinator and automation agent, displays every command's accepted and verified flags, shows simulated device state, and exposes the agent trace. The remaining three domain pages are not connected yet. Pet Care uses the shared coordinator and monitoring agent; no feeder action is requested, so the automation agent is correctly skipped. Each new page should connect through the shared workflow and show the returned assessment, action results, notification outcome and trace.

## Before opening a pull request

Use the project's configured Python environment and start the app from the repository root with `python -m streamlit run app.py`. Open your page from the sidebar and Home services. Confirm that edited inputs reach the handler, changing an input clears any stale result, a new run displays its own outcome, and errors are shown honestly. Check that Overview and Pet Care still work, history filters select the expected saved records, widget keys do not collide, and simulated behavior remains labelled. Include the scenario tested and a screenshot in the pull request.
