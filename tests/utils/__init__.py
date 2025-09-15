def get_env_vars_dict(container_env):
    """
    Convert container environment variables list to a dictionary.
    Args:
        container_env: List of environment variable dictionaries from container spec
    Returns:
        Dictionary mapping env var names to their values or valueFrom references
    """
    return {x["name"]: x["value"] if "value" in x else x["valueFrom"] for x in container_env}


def get_pod_template(doc: dict) -> dict:
    """Given a single doc, return the pod spec.

    doc must be a valid spec for a pod manager. (EG: ds, sts, cronjob, etc.)
    """
    match doc["kind"]:
        case "Deployment" | "StatefulSet" | "ReplicaSet" | "DaemonSet" | "Job":
            return doc["spec"]["template"]
        case "CronJob":
            return doc["spec"]["jobTemplate"]["spec"]["template"]
        case _:
            return {}


def get_containers_by_name(doc: dict, *, include_init_containers=False) -> dict:
    """Given a single doc, return all the containers by name.

    doc must be a valid spec for a pod manager. (EG: ds, sts, cronjob, etc.)
    """

    pod_template = get_pod_template(doc)
    containers = pod_template.get("spec", {}).get("containers", [])
    initContainers = pod_template.get("spec", {}).get("initContainers", [])

    c_by_name = {c["name"]: c for c in containers}

    if include_init_containers and initContainers:
        c_by_name.update({c["name"]: c for c in initContainers})

    return c_by_name
