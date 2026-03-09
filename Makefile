.PHONY: install dev migrate test lint build k8s-deploy k8s-delete help

# Default target
help:
	@echo "Research Marketplace Platform — available targets:"
	@echo ""
	@echo "  install      Install Python dependencies"
	@echo "  dev          Start all services with Docker Compose (hot reload)"
	@echo "  migrate      Run Alembic migrations via Docker Compose"
	@echo "  test         Run the pytest test suite"
	@echo "  lint         Run flake8 linter against app/ and tests/"
	@echo "  build        Build the Docker image locally"
	@echo "  k8s-deploy   Apply all Kubernetes manifests"
	@echo "  k8s-delete   Delete all Kubernetes resources"

# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------

install:
	pip install --upgrade pip
	pip install -r requirements.txt

dev:
	docker-compose up --build

migrate:
	docker-compose --profile migrate run --rm alembic

# ---------------------------------------------------------------------------
# Testing and code quality
# ---------------------------------------------------------------------------

test:
	pytest tests/ -v

lint:
	flake8 app/ tests/ --max-line-length=120 --extend-ignore=E203,W503

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

build:
	docker build -t research-marketplace/backend .

# ---------------------------------------------------------------------------
# Kubernetes
# ---------------------------------------------------------------------------

k8s-deploy:
	kubectl apply -f infrastructure/kubernetes/

k8s-delete:
	kubectl delete -f infrastructure/kubernetes/
