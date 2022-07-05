import base64

from tests.chart_tests.helm_template_generator import render_chart


class TestPgbouncerSecret:
    def test_pgbouncer_secret_defaults(self):
        """Test pgbouncer secret custom server_idle_timeout"""
        docs = render_chart(
            values={
                "airflow": {
                    "pgbouncer": {
                        "enabled": True,
                    },
                },
            },
        )
        doc = [
            doc
            for doc in docs
            if doc["metadata"]["name"] == "release-name-pgbouncer-config"
        ][0]
        ini = base64.b64decode(doc["data"]["pgbouncer.ini"]).decode()

        assert "server_idle_timeout" not in ini

    def test_pgbouncer_secret_custom_server_idle_timeout(self):
        """Test pgbouncer secret custom server_idle_timeout"""
        docs = render_chart(
            values={
                "airflow": {
                    "pgbouncer": {
                        "enabled": True,
                        "extraIni": "server_idle_timeout = 30",
                    },
                },
            },
        )
        doc = [
            doc
            for doc in docs
            if doc["metadata"]["name"] == "release-name-pgbouncer-config"
        ][0]

        ini = base64.b64decode(doc["data"]["pgbouncer.ini"]).decode()

        assert "server_idle_timeout" in ini
