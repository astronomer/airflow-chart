# follow up to https://github.com/astronomer/airflow-chart/pull/301/files
# suite: Test templates/configmap.yaml
#  templates:
#    - charts/airflow/templates/configmaps/webserver-configmap.yaml
#  tests:
#    - it: should work
#      asserts:
#        - isKind:
#            of: ConfigMap
#    - it: should use our default for webserverConfig
#      asserts:
#        - matchRegex:
#            path: data.webserver_config\.py
#            pattern: "CSRF_ENABLED = True"
#        - notMatchRegex:
#            path: data.webserver_config\.py
#            pattern: "AUTH_TYPE = AUTH_REMOTE_USER"
#    - it: should include the astro security manager when enabled
#      set:
#        airflow:
#          useAstroSecurityManager: true
#      asserts:
#        - matchRegex:
#            path: data.webserver_config\.py
#            pattern: "AUTH_TYPE = AUTH_REMOTE_USER"
#        - matchRegex:
#            path: data.webserver_config\.py
#            pattern: "SECURITY_MANAGER_CLASS = AirflowAstroSecurityManager"
#    - it: should still be settable
#      set:
#        airflow:
#          webserver:
#            webserverConfig: "# well hello"
#      asserts:
#        - matchRegex:
#            path: data.webserver_config\.py
#            pattern: "# well hello"
