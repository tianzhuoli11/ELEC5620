# Streamlit user interface

Store Python/Streamlit views, shared components, navigation, layout, styling, event inputs and result displays here. The team must nominate a UI integration lead; each domain owner supplies their inputs, outputs and scenarios.

Suggested views: household overview, five domain views, device state, agent processing steps and audit history. Clearly mark simulated events and devices.

A root `app.py` will register/call these views; the entry point and navigation implementation are not included yet.

Call shared agents or application handlers and display actual outcomes. Do not duplicate domain rules or directly operate devices in page code. Option A does not introduce a React frontend or FastAPI backend; UI and business logic still remain separate.
