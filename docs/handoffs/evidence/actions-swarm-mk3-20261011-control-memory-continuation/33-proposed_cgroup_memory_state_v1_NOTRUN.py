"""Proposed pure memory admission/state; no filesystem/process/native operations."""
CGROUP_INITIAL_HEADROOM_BYTES = 3113851289  # Proposed 2.4 GiB workload + 0.5 GiB reserve.
CGROUP_RESERVE_BYTES = 536870912
OOM_FIELDS = ("oom", "oom_kill", "oom_group_kill")

class MemoryAdmissionError(ValueError):
    pass

def require(ok, code):
    if not ok:
        raise MemoryAdmissionError(code)

def snapshot(value):
    require(type(value) is dict and set(value) == {"identity", "max", "current", "events", "events_local"}, "MEMORY_SCHEMA")
    require(type(value["identity"]) is tuple and len(value["identity"]) == 3
            and type(value["identity"][0]) is str and value["identity"][0]
            and all(type(v) is int and v >= 0 for v in value["identity"][1:]), "MEMORY_IDENTITY")
    require(type(value["max"]) is int and value["max"] > 0
            and type(value["current"]) is int and value["current"] >= 0, "MEMORY_FINITE_COUNTER")
    for key in ("events", "events_local"):
        require(type(value[key]) is dict and set(OOM_FIELDS).issubset(value[key])
                and all(type(k) is str and type(v) is int and v >= 0 for k, v in value[key].items()), "MEMORY_EVENT_COUNTER")
    return {**value, "events": dict(value["events"]), "events_local": dict(value["events_local"])}

def admit_before(value):
    observed = snapshot(value)
    require(observed["max"] - observed["current"] >= CGROUP_INITIAL_HEADROOM_BYTES,
            "MEMORY_INITIAL_HEADROOM")
    return observed

class MemoryState:
    def __init__(self, before):
        self.before = admit_before(before)
        self.minimum_headroom = self.before["max"] - self.before["current"]
        self.samples = 0
        self.primary = None
        self.signal_record = None
        self.previous = self.before

    def observe(self, value):
        # Caller applies existing owner selection/authorize_signal, never this module.
        if self.primary is not None:
            return self.primary
        try:
            observed = snapshot(value)
            require(observed["identity"] == self.before["identity"]
                    and observed["max"] == self.before["max"], "MEMORY_IDENTITY_CHANGED")
            for table in ("events", "events_local"):
                require(set(observed[table]) == set(self.previous[table])
                        and all(observed[table][key] >= number for key, number in self.previous[table].items()),
                        "MEMORY_EVENT_RESET_OR_SCHEMA_CHANGED")
            self.samples += 1
            headroom = observed["max"] - observed["current"]
            self.minimum_headroom = min(self.minimum_headroom, headroom)
            reason = "MEMORY_RESERVE_THRESHOLD" if headroom <= CGROUP_RESERVE_BYTES else None
            if any(observed[table][key] > self.before[table][key]
                   for table in ("events", "events_local") for key in OOM_FIELDS):
                reason = "MEMORY_OOM_COUNTER_INCREASE"
            self.previous = observed
            if reason:
                self.primary = {"status": "FAIL", "code": reason}
        except MemoryAdmissionError as error:
            self.primary = {"status": "FAIL", "code": str(error)}
        except Exception:
            self.primary = {"status": "FAIL", "code": "MEMORY_INSPECTION_UNAVAILABLE"}
        return self.primary
