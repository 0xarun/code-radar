PYTHON ?= python3

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

migrate:
	alembic upgrade head

worker:
	$(PYTHON) -m app.workers.runner

format:
	$(PYTHON) -m pip install ruff > /dev/null 2>&1 || true
	ruff format app

lint:
	$(PYTHON) -m pip install ruff > /dev/null 2>&1 || true
	ruff check app
