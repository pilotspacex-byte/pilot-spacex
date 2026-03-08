{{/*
Expand the name of the chart.
*/}}
{{- define "pilot-space.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "pilot-space.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "pilot-space.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to all resources.
*/}}
{{- define "pilot-space.labels" -}}
helm.sh/chart: {{ include "pilot-space.chart" . }}
app.kubernetes.io/name: {{ include "pilot-space.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels — stable subset used in matchLabels (must not change after first deploy).
*/}}
{{- define "pilot-space.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pilot-space.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend component labels.
*/}}
{{- define "pilot-space.backendLabels" -}}
{{ include "pilot-space.labels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Backend selector labels.
*/}}
{{- define "pilot-space.backendSelectorLabels" -}}
{{ include "pilot-space.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend component labels.
*/}}
{{- define "pilot-space.frontendLabels" -}}
{{ include "pilot-space.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend selector labels.
*/}}
{{- define "pilot-space.frontendSelectorLabels" -}}
{{ include "pilot-space.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Backend service name.
*/}}
{{- define "pilot-space.backendName" -}}
{{- printf "%s-backend" (include "pilot-space.fullname" .) }}
{{- end }}

{{/*
Frontend service name.
*/}}
{{- define "pilot-space.frontendName" -}}
{{- printf "%s-frontend" (include "pilot-space.fullname" .) }}
{{- end }}
