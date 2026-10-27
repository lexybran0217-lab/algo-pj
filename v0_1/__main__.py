import time

started_at = time.perf_counter()

from .cli import main

raise SystemExit(main(started_at=started_at))
