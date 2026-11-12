from actions import action, data


@action
def report(value: str) -> dict:
    """Read only the exact prepared Data operation."""
    return {"record_id": data.scan("records", "records.scan/v1")[0]["record_id"] + "-" + value}
