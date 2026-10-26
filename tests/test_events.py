from sentinel.events import EventBus, make_event


async def test_publish_reaches_subscribers_and_history():
    bus = EventBus()
    got = []

    async def handler(ev):
        got.append(ev.type)

    bus.subscribe(handler)
    await bus.publish(make_event("decision", "ses_1", None, {"x": 1}))
    assert got == ["decision"]
    assert [e.type for e in bus.recent()] == ["decision"]


async def test_failing_handler_does_not_stop_others():
    bus = EventBus()
    got = []

    async def bad(ev):
        raise RuntimeError("console crashed")

    async def good(ev):
        got.append(ev.type)

    bus.subscribe(bad)
    bus.subscribe(good)
    await bus.publish(make_event("freeze", "ses_1", None))
    assert got == ["freeze"]


async def test_unsubscribe_and_type_filter():
    bus = EventBus()
    got = []

    async def handler(ev):
        got.append(ev.type)

    unsubscribe = bus.subscribe(handler, event_type="decision")
    await bus.publish(make_event("audit.record", None, None))
    await bus.publish(make_event("decision", None, None))
    unsubscribe()
    await bus.publish(make_event("decision", None, None))
    assert got == ["decision"]


async def test_history_is_bounded():
    bus = EventBus(history=3)
    for i in range(5):
        await bus.publish(make_event("t", None, None, {"i": i}))
    assert [e.payload["i"] for e in bus.recent()] == [2, 3, 4]
