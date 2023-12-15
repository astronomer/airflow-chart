# Chart testing

In November 2021 Astronomer switched from using the `helm-unittest` software to using a `pytest` setup for testing the [astronomer/airflow-chart](https://github.com/astronomer/airflow-chart) helm chart. This mirrors the Airflow community's effort in chart testing. There are many good reasons reasons for choosing `pytest` over the more helm-specific `helm-unittest` software:

- pytest skills are something you can learn and take with you pretty much anywhere.
- pytest skills are something engineers can bring to the table without having any inside knowledge of Astronomer, Airflow, kubernetes or helm.
- pytest is extensively documented, has many useful plugins, and is debuggable though all the normal python testing tools.

See [astronomer/astronomer/tests/chart_tests/README.md](https://github.com/astronomer/astronomer/blob/master/tests/chart_tests/README.md) for a tutorial on how to write these tests.
