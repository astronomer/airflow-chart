# Adding all helper functions to be imported by other modules
def get_containers_by_name(doc, include_init_containers=False):
    """Given a single doc, return all the containers by name.

    doc must be a valid spec for a pod manager. (EG: ds, sts)
    """

    c_by_name = {c["name"]: c for c in doc["spec"]["template"]["spec"]["containers"]}

    if include_init_containers and doc["spec"]["template"]["spec"].get(
        "initContainers"
    ):
        c_by_name |= {
            c["name"]: c for c in doc["spec"]["template"]["spec"].get("initContainers")
        }

    return c_by_name
