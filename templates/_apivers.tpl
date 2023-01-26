{{- define "apiVersion.HorizontalPodAutoscaler" -}}
{{- if semverCompare "<1.25-0" .Capabilities.KubeVersion.Version -}}
autoscaling/v2beta1
{{- else -}}
autoscaling/v2
{{- end -}}
{{- end}}
