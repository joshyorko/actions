import re as _re
from typing import List

__version__ = "1.1.0a19"
version_info = [int(x) for x in _re.findall(r"\d+", __version__)[:3]]

__all__: List[str] = []
