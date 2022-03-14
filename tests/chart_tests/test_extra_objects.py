# follow up to https://github.com/astronomer/airflow-chart/pull/301/files
# suite: Test templates/extra-objects.yaml
#  templates:
#    - templates/extra-objects.yaml
#  tests:
#    - it: should be empty be default
#      asserts:
#        - hasDocuments:
#            count: 0
#    - it: should add extra objects
#      set:
#        something: world
#        extraObjects:
#          - name: "hello {{ .Values.something }}"
#            another:
#              something: yes
#      asserts:
#        - hasDocuments:
#            count: 1
#        - equal:
#            path: name
#            value: "hello world"
#        - equal:
#            path: another.something
#            value: yes
#    - it: should handle multiples
#      set:
#        extraObjects:
#          - name: hello
#            another:
#              something: yes
#          - name: number2
#      asserts:
#        - hasDocuments:
#            count: 2
#        # and further testing with documentId appears to be broken :(
