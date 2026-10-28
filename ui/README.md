# Streamlit user interface

Energy & Comfort now also has a separate explicitly approved simulated-control panel. It uses the context entered above, requires fresh clear results from both safety domains, saves actual action outcomes, and exposes offline failures. Its original assessment button remains assessment-only. See [integrated control review](../docs/INTEGRATED_CONTROL_REVIEW.md).

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

Energy & Comfort is registered from `ui/energy_comfort.py` as `"Energy & Comfort": render_energy_comfort`. The sidebar and Overview's Home services section open the registered function automatically. Home services receives the registered domain names from `app.py`, so its availability labels follow the registry. Unregistered domains retain their pending page. Registration alone does not add a domain's readings to Overview metrics or history; coordinate those shared displays with the UI integration owner.

## Keep pages compatible

- Reuse Streamlit controls and the styles applied by `app.py`. Do not call `st.set_page_config()` or inject a replacement theme in a domain page. The interface does not require external images or font downloads.
- Prefix widget keys and session-state entries with your domain, for example `elderly_safety_scenario`, to avoid collisions.
- Put business rules in `domains/`, shared agent orchestration in `agents/`, and device access in `tools/`. Pages should call those interfaces, not duplicate rules or operate devices directly.
- Show the result returned by the handler, including failures. Clearly label sample readings and simulated actions; report notifications or device changes only when the result confirms them.
- Keep API keys in local configuration. Do not place keys in page code, screenshots, or committed files.

## Current integration status

Overview and Pet Care share a working sample-input workspace. Presets initialise the reading; the `pet_value` input lets users change it before running a check. The page creates a sensor event with `simulation.events.make_sensor_event`, calls `domains.pet_care.integration.monitor_pet_workflow`, and displays the saved assessment, shared workflow trace and simulated owner-alert outcome. Saved readings feed the summary metrics and history filters. These are simulated inputs, not live sensor connections.

Smart Home Control is connected. Its page creates a direct user-goal event, runs the shared coordinator and automation agent, displays every command's accepted and verified flags, shows simulated device state, and exposes the agent trace. Pet Care's feeder demonstration is optional and requires an explicit simulated request; ordinary monitoring does not operate a feeder.

Elderly Safety is connected with simulated fall assessment, resident confirmation and caregiver escalation. Home Security is connected with fictional sensor presets, LOW/MEDIUM/HIGH response, homeowner confirmation, verified simulated device actions and OR-06 external warning scenarios. Energy & Comfort is connected for assessment-only evaluation: simulated context inputs, shared-workflow assessment, fail-closed eligibility and deterministic explanations. The assessment button does not dispatch devices. Its separate adjustment panel now executes approved simulated plans using fresh cross-domain safety evidence, with per-command rechecks and independent state verification. Each new page should connect through the shared workflow and show the returned assessment, action results, notification outcome and trace.

## Before opening a pull request

Use the project's configured Python environment and start the app from the repository root with `python -m streamlit run app.py`. Open your page from the sidebar and Home services. Confirm that edited inputs reach the handler, changing an input clears any stale result, a new run displays its own outcome, and errors are shown honestly. Check that Overview and Pet Care still work, history filters select the expected saved records, widget keys do not collide, and simulated behavior remains labelled. Include the scenario tested and a screenshot in the pull request.
