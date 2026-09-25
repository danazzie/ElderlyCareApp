.PHONY: install dev api web build test evals evals-ab smoke docker

install:            ## backend + frontend deps
	python3 -m venv .venv && .venv/bin/pip install -r services/api/requirements.txt
	cd apps/web && npm install

api:                ## run the API (serves built web app too)
	cd services/api && ../../.venv/bin/uvicorn app.main:app --reload --port 8000

web:                ## run the web app in dev mode (proxies /api to :8000)
	cd apps/web && npm run dev

build:              ## production build of the web app
	cd apps/web && npm run build

test:
	cd services/api && ../../.venv/bin/python -m pytest tests/ -q

evals:              ## full golden dataset run (39 cases)
	.venv/bin/python evals/run.py

evals-ab:           ## A/B experiment: RAG variant A vs B
	.venv/bin/python evals/run.py --ab

smoke:              ## 10-case CI smoke evals
	.venv/bin/python evals/run.py --smoke

docker:
	docker compose -f infra/docker-compose.yml up --build
