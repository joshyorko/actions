from actions import action
from pydantic import BaseModel

class Point(BaseModel):
    label: str
    value: int
class Entry(BaseModel):
    message: str
class Details(BaseModel):
    name: str
    count: int
class Report(BaseModel):
    rows: list[Point]
    logs: list[Entry]
    details: Details

@action
def report(text: str) -> Report:
    """Produce an independently generated bounded report."""
    if text == "fail":
        raise ValueError("Synthetic requested failure")
    words = text.split()
    return Report(rows=[Point(label="words", value=len(words))],
        logs=[Entry(message="Processed " + text)],
        details=Details(name=text, count=len(words)))
