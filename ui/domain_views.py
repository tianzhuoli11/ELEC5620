"""One registration point for independently implemented domain pages."""

from collections.abc import Callable

from ui.dashboard import render_pending, render_pet_care


DOMAIN_VIEWS: dict[str, Callable[[], None]] = {
    "Pet Care": render_pet_care,
    # Import a teammate's render function above, then register its domain here.
    # "Elderly Safety": render_elderly_safety,
}


def render_domain(name: str) -> None:
    renderer = DOMAIN_VIEWS.get(name)
    if renderer is None:
        render_pending(name)
    else:
        renderer()
