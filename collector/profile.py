import yaml

from collector.schema import DRONE_FIELDS, DRONE_REQUIRED


def template(name="my_drone"):
    p = {k: None for k in DRONE_FIELDS}
    p["name"] = name
    p["notes"] = "Fill in every field you know. Weigh the drone with battery, ready to fly."
    return p


def save(profile, path):
    with open(path, "w") as f:
        yaml.safe_dump(profile, f, sort_keys=False)


def load(path):
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return {k: data.get(k) for k in DRONE_FIELDS}


def missing(profile):
    return [k for k in DRONE_REQUIRED if not profile.get(k)]
