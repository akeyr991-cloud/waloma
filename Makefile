.PHONY: install migrate run test admin
install:
	pip install -r requirements.txt
migrate:
	alembic upgrade head
run:
	uvicorn app.main:app --reload
test:
	pytest -q
admin:
	python -m scripts.create_admin
