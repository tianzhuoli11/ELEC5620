# UC-05 Energy & Comfort — 2-minute demonstration script (English)

**Audience:** Stage 2 assessors. **App:** `streamlit run app.py` from commit `2d035f6`. **Duration:** ~2 minutes. **Scope:** Simulated home only.

**Say upfront:** “All sensors and devices are simulated. Successful device readback does not mean the room got cooler or that energy was saved.”

## Before you start

- Use a **fresh browser session** (or restart Streamlit) so `SafetyState` is empty.
- Do **not** enable campus AI for this path.
- Expected local audit file: `data/runtime/energy_comfort.jsonl` (created on run; git-ignored).

## Step 1 — Clear cross-domain safety (~40 s)

1. Sidebar → **Home Security**.
2. Leave scenario **normal** (default). Click **Run assessment** (button key `security_run`).
3. **Expected:** Workflow completes; no blocking hazard for normal scenario.
4. Sidebar → **Elderly Safety**.
5. Scenario: **Fall, then not moving (30 s)**. Click **Run scenario** (`run-elderly-scenario`).
6. **Expected:** Confirmation prompt; safety not clear yet.
7. Click quick reply **I'm fine** (`quick-I'm fine`).
8. **Expected:** Green session message on Energy page later: both safety domains clear (or equivalent success on Elderly banner).
9. Sidebar → **Energy & Comfort**.
10. **Expected:** Panel **Session safety** shows clear for simulated control (success/info), not “Not clear”.

**If step 10 shows not clear:** repeat Security normal + Elderly safe reply; do not proceed to control.

## Step 2 — Assessment only (~20 s)

1. Scenario preset: **Too warm (occupied)** (loads 27 °C, prefs 20–24).
2. Click **Run assessment →** (`run-energy-assessment`).
3. **Expected:**
   - Decision **ADJUSTMENT_NEEDED**.
   - Scope line includes **`ASSESSMENT_ONLY`** and **`FORMAL_CONTROL_PENDING`**.
   - Caption: no device command dispatched; execution **NOT_EXECUTED**.

## Step 3 — Explicit simulated control + readback (~40 s)

1. Scroll to **Run a simulated adjustment (EXPLICIT_SIMULATION)**.
2. Check **Approve this simulated adjustment** (`energy_execution_approval`).
3. Control device fault: **None**.
4. Click **Run simulated adjustment** (`run-energy-control`).
5. **Expected:**
   - Reason mentions explicitly approved simulated control.
   - Workflow outcome **COMPLETE** (for this preset).
   - Table of **action results** with verified successes (curtain + AC for “too warm occupied”).
   - Caption contains **`UNKNOWN_NOT_MEASURED`** for environment (not a PASS for comfort/savings).
   - JSON audit includes `selected_plan`, `post_action_environment`, `ui_mode: EXPLICIT_SIMULATION`.

**Do not say:** “The room temperature is now 24 °C measured” — only device state was verified.

## Step 4 — Safety blocks further energy action (~20 s)

1. Sidebar → **Home Security**.
2. Scenario: **smoke**. Click **Run assessment**.
3. Sidebar → **Energy & Comfort** (approval can stay checked).
4. Click **Run simulated adjustment** again.
5. **Expected:**
   - **No** new device actions (`action_results` empty or warning).
   - Safety snapshot not clear; blocking reason mentions home security / hazard.

## Reproducibility check

Automated equivalent: `tests/test_energy_comfort_ui.py::test_actual_safety_pages_enable_energy_then_smoke_blocks_it` — **PASS** on `2d035f6` (Streamlit AppTest).

Manual-only variance: widget timing, first-load session state, or stale browser tab — use a fresh session if control runs before safety clear.

## Optional 15 s closing (Decision explanations)

If time allows: sidebar **Decision explanations** → select the latest Energy control record → ask a trade-off question. **Expected:** Explanation cites recorded plan and states unknown environmental effect (OR-05), without inventing savings.
