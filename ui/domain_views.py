"""One registration point for independently implemented domain pages."""

from collections.abc import Callable

from ui.dashboard import render_pending, render_pet_care
from ui.elderly_safety import render_elderly_safety
from ui.smart_home_control import render_smart_home_control


DOMAIN_VIEWS: dict[str, Callable[[], None]] = {
    "Pet Care": render_pet_care,
    "Smart Home Control": render_smart_home_control,
    "Elderly Safety": render_elderly_safety,
    # Import a teammate's render function above, then register its domain here.
}


def render_domain(name: str) -> None:
    renderer = DOMAIN_VIEWS.get(name)
    if renderer is None:
        render_pending(name)
    else:
        renderer()
