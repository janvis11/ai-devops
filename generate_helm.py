import os

apps = ["api", "worker", "frontend"]

base_dir = r"d:\devops\k8s\apps"

for app in apps:
    app_dir = os.path.join(base_dir, app)
    templates_dir = os.path.join(app_dir, "templates")
    os.makedirs(templates_dir, exist_ok=True)

    # Chart.yaml
    with open(os.path.join(app_dir, "Chart.yaml"), "w") as f:
        f.write(f"""apiVersion: v2
name: {app}
description: A Helm chart for Kubernetes
type: application
version: 0.1.0
appVersion: "1.0.0"
""")

    # values.yaml
    with open(os.path.join(app_dir, "values.yaml"), "w") as f:
        f.write(f"""replicaCount: 1

image:
  repository: ghcr.io/janvis11/devops.ai-{app}
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: {8000 if app == 'api' else 3000 if app == 'frontend' else 80}

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 100m
    memory: 128Mi
""")

    # deployment.yaml
    with open(os.path.join(templates_dir, "deployment.yaml"), "w") as f:
        f.write(f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{{{ include "{app}.fullname" . }}}}
  labels:
    app: {{{{ .Chart.Name }}}}
spec:
  replicas: {{{{ .Values.replicaCount }}}}
  selector:
    matchLabels:
      app: {{{{ .Chart.Name }}}}
  template:
    metadata:
      labels:
        app: {{{{ .Chart.Name }}}}
    spec:
      containers:
        - name: {{{{ .Chart.Name }}}}
          image: "{{{{ .Values.image.repository }}}}:{{{{ .Values.image.tag | default .Chart.AppVersion }}}}"
          imagePullPolicy: {{{{ .Values.image.pullPolicy }}}}
          ports:
            - name: http
              containerPort: {{{{ .Values.service.port }}}}
              protocol: TCP
          resources:
            {{{{- toYaml .Values.resources | nindent 12 }}}}
""")

    # service.yaml
    if app in ['api', 'frontend']:
        with open(os.path.join(templates_dir, "service.yaml"), "w") as f:
            f.write(f"""apiVersion: v1
kind: Service
metadata:
  name: {{{{ include "{app}.fullname" . }}}}
  labels:
    app: {{{{ .Chart.Name }}}}
spec:
  type: {{{{ .Values.service.type }}}}
  ports:
    - port: {{{{ .Values.service.port }}}}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    app: {{{{ .Chart.Name }}}}
""")

    # _helpers.tpl
    with open(os.path.join(templates_dir, "_helpers.tpl"), "w") as f:
        f.write(f"""{{{{/*
Expand the name of the chart.
*/}}}}
{{{{- define "{app}.name" -}}}}
{{{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}}}
{{{{- end }}}}

{{{{/*
Create a default fully qualified app name.
*/}}}}
{{{{- define "{app}.fullname" -}}}}
{{{{- .Release.Name }}-{{ .Chart.Name }}}}
{{{{- end }}}}
""")

print("Helm charts generated successfully.")
