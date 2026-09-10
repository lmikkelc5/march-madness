import json

from config import STATE_DIR


def _state_file(job_name):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{job_name}.json"


def _load(job_name):
    path = _state_file(job_name)
    if not path.exists():
        return set()
    return set(json.loads(path.read_text()))


def is_done(job_name, key):
    return key in _load(job_name)


def mark_done(job_name, key):
    done = _load(job_name)
    done.add(key)
    _state_file(job_name).write_text(json.dumps(sorted(done), indent=2))
