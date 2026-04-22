import pytest

from tests.utils.chart import render_chart

cron_test_data = [
    ("development-angular-system-6091", 3),
    ("development-arithmetic-phases-5695", 3),
    ("development-empty-aurora-8527", 3),
    ("development-explosive-inclination-4552", 3),
    ("development-infrared-nadir-2873", 3),
    ("development-barren-telemetry-6087", 4),
    ("development-geocentric-cluster-5666", 4),
    ("development-mathematical-supernova-1523", 4),
    ("development-cometary-terrestrial-2880", 5),
    ("development-nuclear-gegenschein-1657", 5),
    ("development-quasarian-telescope-4189", 5),
    ("development-traditional-universe-0643", 5),
    ("development-asteroidal-space-6369", 6),
    ("development-blazing-horizon-1542", 6),
    ("development-boreal-inclination-4658", 6),
    ("development-exact-ionosphere-3963", 6),
    ("development-extrasolar-meteor-4188", 6),
    ("development-inhabited-dust-4345", 6),
    ("development-nebular-singularity-6518", 6),
    ("development-arithmetic-sky-0424", 7),
    ("development-true-century-8320", 7),
    ("development-angular-radian-2199", 8),
    ("development-scientific-cosmonaut-1863", 8),
    ("development-uninhabited-wavelength-9355", 8),
    ("development-false-spacecraft-1944", 9),
    ("development-mathematical-equator-2284", 9),
    ("development-amateur-horizon-3115", 12),
    ("development-devoid-terminator-0587", 12),
    ("development-optical-asteroid-4621", 12),
]


@pytest.mark.parametrize("release_name,result_minute", cron_test_data, ids=[x[0] for x in cron_test_data])
def test_cron_splay(release_name, result_minute):
    """Test that our adler32sum method of generating deterministic random numbers works. This test
    ensures the apache/airflow chart continues to work as we expect it to work."""

    docs = render_chart(
        name=release_name,
        show_only=["charts/airflow/templates/cleanup/cleanup-cronjob.yaml"],
        values={
            "airflow": {
                "cleanup": {
                    "enabled": True,
                    "schedule": '{{- add 3 (regexFind ".$" (adler32sum .Release.Name)) -}}-59/15 * * * *',
                },
            },
        },
    )

    assert docs[0]["spec"]["schedule"] == f"{result_minute}-59/15 * * * *"
