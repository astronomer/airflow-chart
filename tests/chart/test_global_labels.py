import pytest

from tests.chart import get_all_features
from tests.chart.helm_template_generator import render_chart

POD_MANAGER_SPEC_LABEL_PATH = {
    "StatefulSet": "spec.template.metadata.labels",
    "Deployment": "spec.template.metadata.labels",
    "CronJob": "spec.jobTemplate.spec.template.metadata.labels",
    "Job": "spec.template.metadata.labels",
    "DaemonSet": "spec.template.metadata.labels",
    "Pod": "metadata.labels",
}


def get_labels_from_object(obj) -> str | None:
    """Helper to get nested dictionary value using dot notation path.

    Example:
        path = "spec.template.metadata.labels" returns obj["spec"]["template"]["metadata"]["labels"]
    """
    if not (path := POD_MANAGER_SPEC_LABEL_PATH.get(obj.get("kind", ""), "")):
        return None
    keys = path.split(".")
    current = obj
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return None


def get_labels_from_pod_managers(docs: list) -> dict:
    """Given a list of docs, return a dict of all pod labels for any pod managers in the list.

    Returns a dictionary mapping resource names to their labels.
    """
    pod_docs = []

    for doc in docs:
        if not isinstance(doc, dict) or "kind" not in doc or "metadata" not in doc:
            continue

        kind = doc["kind"]

        if kind not in POD_MANAGER_SPEC_LABEL_PATH:
            continue
        pod_labels = get_labels_from_object(doc)

        if pod_labels is None:
            continue

        metadata = doc.get("metadata", {})
        name = metadata.get("name", "unknown")

        pod_docs.append({"name": name, "kind": kind, "labels": pod_labels})

    return {f"{doc['kind']}_{doc['name']}": doc["labels"] for doc in pod_docs}


values = get_all_features()
values["labels"] = {"test-label-1": "test-value-1"}
values["airflow"]["labels"] = {"test-label-1": "test-value-1"}

docs = render_chart(values=values)
# postgres is not our chart and is only for dev, so we skip it
label_data = {k: v for k, v in get_labels_from_pod_managers(docs).items() if not k.endswith("postgresql")}


@pytest.mark.parametrize("resource_name,pod_labels", list(label_data.items()), ids=list(label_data.keys()))
def test_label_overrides(resource_name, pod_labels):
    """Ensure that all pods get labels when using value overrides."""

    assert "test-label-1" in pod_labels, f"Label 'test-label-1' not found in {resource_name}"
    assert pod_labels["test-label-1"] == "test-value-1", f"Label 'test-label-1' has unexpected value in {resource_name}"
