# infra/Makefile — devops.ai Infrastructure Management
# Usage: make <target>
# Run from the infra/ directory or use `make -C infra <target>` from repo root.

.PHONY: bootstrap teardown kafka-up kafka-down agent-up agent-down \
        tf-init tf-plan tf-apply tf-destroy \
        ansible-k3s ansible-secrets ansible-kafka \
        security-apply opa-apply \
        help

SHELL := /bin/bash
REPO_ROOT := $(shell git rev-parse --show-toplevel)
ANSIBLE_DIR := $(REPO_ROOT)/infra/ansible
TERRAFORM_DIR := $(REPO_ROOT)/infra/terraform


help:
	@echo ""
	@echo "devops.ai Infrastructure Makefile"
	@echo "============================"
	@echo ""
	@echo "Bootstrap targets:"
	@echo "  bootstrap          Full cluster bootstrap (Terraform + Ansible + Helm)"
	@echo "  teardown           Destroy all infrastructure"
	@echo ""
	@echo "Terraform targets:"
	@echo "  tf-init            terraform init"
	@echo "  tf-plan            terraform plan"
	@echo "  tf-apply           terraform apply"
	@echo "  tf-destroy         terraform destroy"
	@echo ""
	@echo "Ansible targets:"
	@echo "  ansible-k3s        Install k3s on all nodes"
	@echo "  ansible-secrets    Bootstrap Vault secrets"
	@echo "  ansible-kafka      Start local Kafka cluster"
	@echo ""
	@echo "Kafka targets:"
	@echo "  kafka-up           Start Kafka docker-compose cluster"
	@echo "  kafka-down         Stop Kafka cluster"
	@echo ""
	@echo "Security targets:"
	@echo "  security-apply     Apply all security manifests (RBAC + NetworkPolicy)"
	@echo "  opa-apply          Apply OPA ConstraintTemplates and Constraints"
	@echo ""
	@echo "Agent targets:"
	@echo "  agent-up           Deploy devops.ai agent to k3s"
	@echo "  agent-down         Remove devops.ai agent from k3s"
	@echo ""


bootstrap: tf-apply ansible-k3s security-apply opa-apply ansible-secrets
	@echo ""
	@echo "✅ devops.ai platform bootstrap complete!"
	@echo "   Next: make kafka-up && helmfile apply"


teardown: kafka-down
	cd $(REPO_ROOT) && helmfile destroy || true
	cd $(TERRAFORM_DIR) && terraform destroy -auto-approve


tf-init:
	cd $(TERRAFORM_DIR) && terraform init

tf-plan:
	cd $(TERRAFORM_DIR) && terraform plan

tf-apply:
	cd $(TERRAFORM_DIR) && terraform init && terraform apply -auto-approve

tf-destroy:
	cd $(TERRAFORM_DIR) && terraform destroy -auto-approve


ansible-k3s:
	ansible-playbook \
		-i $(ANSIBLE_DIR)/inventory/hosts.yml \
		$(ANSIBLE_DIR)/playbooks/install-k3s.yml \
		--diff

ansible-secrets:
	@echo "Ensure VAULT_TOKEN, CLAUDE_API_KEY, KAFKA_PASSWORD, PG_PASSWORD are set"
	ansible-playbook \
		-i $(ANSIBLE_DIR)/inventory/hosts.yml \
		$(ANSIBLE_DIR)/playbooks/bootstrap-secrets.yml \
		--diff

ansible-kafka:
	ansible-playbook \
		-i $(ANSIBLE_DIR)/inventory/hosts.yml \
		$(ANSIBLE_DIR)/playbooks/install-kafka-local.yml \
		--diff


kafka-up:
	docker compose -f $(REPO_ROOT)/kafka/docker-compose.yml up -d
	@sleep 15
	bash $(REPO_ROOT)/kafka/topics/create-topics.sh
	@echo "kafka-ui: http://localhost:8080"

kafka-down:
	docker compose -f $(REPO_ROOT)/kafka/docker-compose.yml down


security-apply:
	kubectl apply -f $(REPO_ROOT)/k8s/security/rbac/
	kubectl apply -f $(REPO_ROOT)/k8s/security/networkpolicy/
	@echo "✅ RBAC and NetworkPolicies applied"


opa-apply:
	@echo "Applying OPA ConstraintTemplates (wait for CRD creation)..."
	kubectl apply -f $(REPO_ROOT)/k8s/security/opa/no-latest-tag-template.yaml
	kubectl apply -f $(REPO_ROOT)/k8s/security/opa/require-resource-limits-template.yaml
	kubectl apply -f $(REPO_ROOT)/k8s/security/opa/protect-devops-ai-system-template.yaml
	@echo "Waiting 10s for CRDs to be registered..."
	@sleep 10
	@echo "Applying OPA Constraints..."
	kubectl apply -f $(REPO_ROOT)/k8s/security/opa/no-latest-tag-constraint.yaml
	kubectl apply -f $(REPO_ROOT)/k8s/security/opa/require-resource-limits-constraint.yaml
	kubectl apply -f $(REPO_ROOT)/k8s/security/opa/protect-devops-ai-system-constraint.yaml
	@echo "✅ OPA policies applied"


vault-setup:
	bash $(REPO_ROOT)/k8s/security/vault-auth-setup.sh

agent-up:
	kubectl apply -f $(REPO_ROOT)/k8s/devops-ai-system/
	@echo "✅ devops.ai agent deployed"

agent-down:
	kubectl delete -f $(REPO_ROOT)/k8s/devops-ai-system/ || true
