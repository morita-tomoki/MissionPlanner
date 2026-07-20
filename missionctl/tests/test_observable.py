from missionctl.core.util.observable import Observable


def test_emits_current_on_subscribe() -> None:
    obs: Observable[int] = Observable(1)
    seen: list[int] = []
    obs.subscribe(seen.append)
    assert seen == [1]


def test_emits_on_set() -> None:
    obs: Observable[int] = Observable(0)
    seen: list[int] = []
    obs.subscribe(seen.append, emit_current=False)
    obs.set(5)
    obs.set(7)
    assert seen == [5, 7]
    assert obs.value == 7


def test_unsubscribe_stops_delivery() -> None:
    obs: Observable[int] = Observable(0)
    seen: list[int] = []
    sub = obs.subscribe(seen.append, emit_current=False)
    obs.set(1)
    sub.dispose()
    obs.set(2)
    assert seen == [1]


def test_unsubscribe_is_by_token_not_value() -> None:
    # Regression guard against the legacy GetHashCode-collision unsubscribe bug:
    # two identical observers must be tracked independently, and disposing one
    # must not remove the other.
    obs: Observable[int] = Observable(0)
    seen: list[int] = []
    cb = seen.append
    s1 = obs.subscribe(cb, emit_current=False)
    obs.subscribe(cb, emit_current=False)
    obs.set(1)  # both fire -> two entries
    s1.dispose()  # removes only the first subscription
    obs.set(2)  # one fires -> one entry
    assert seen == [1, 1, 2]


def test_subscription_context_manager() -> None:
    obs: Observable[int] = Observable(0)
    seen: list[int] = []
    with obs.subscribe(seen.append, emit_current=False):
        obs.set(1)
    obs.set(2)  # delivered after the context exits -> ignored
    assert seen == [1]
