import os

from dagster.core.errors import DagsterInvariantViolationError

DAGSTER_CONFIG_YAML_FILENAME = "dagster.yaml"


def is_dagster_home_set():
    return bool(os.getenv('DAGSTER_HOME'))


def dagster_home():
    dagster_home_path = os.getenv('DAGSTER_HOME')

    if not dagster_home_path:
        raise DagsterInvariantViolationError(
            'DAGSTER_HOME is not set, check is_dagster_home_set before invoking.'
        )

    return os.path.expanduser(dagster_home_path)
