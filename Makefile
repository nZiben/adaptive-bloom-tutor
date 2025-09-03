run-backend:
	uvicorn backend.app.main:app --host $${API_HOST:-0.0.0.0} --port $${API_PORT:-8000} --reload

run-frontend:
	streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0

seed:
	python -c "from backend.app.rag.vectorstore import seed_if_empty; seed_if_empty()"

init-bucket:
	python -c "from backend.app.s3_client import ensure_bucket; ensure_bucket()"

up:
	docker compose up --build
