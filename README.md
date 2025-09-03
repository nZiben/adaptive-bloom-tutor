# AI-Tutor (скользящая диагностика)

## Быстрый старт (локально)
1. Скопируйте `.env.example` → `.env` и заполните `MISTRAL_API_KEY`.
2. Установите зависимости: `pip install -r requirements.txt`.
3. Инициализируйте хранилища:
   - `python -c "from backend.app.s3_client import ensure_bucket; ensure_bucket()"`
   - `python -c "from backend.app.rag.vectorstore import seed_if_empty; seed_if_empty()"`
4. Запустите бэкенд:  
   `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`
5. Запустите фронтенд:  
   `streamlit run frontend/streamlit_app.py`
6. Откройте `http://localhost:8501`.

## Через docker-compose
1. Создайте `.env` из `.env.example`.
2. `make up` или `docker compose up --build`.

## Что внутри
- **Streamlit** чат-клиент.
- **FastAPI** бэкенд с FSM/policy (режимы `exam` и `diagnostic`):
  - Многоагентный слой: `Tutor` (RAG на ChromaDB + Mistral), `Judge/Scorer` (JSON), `Bloom-Tagger`, `Planner`, `Summarizer`.
  - **Assessment Engine**: EMA + 2PL IRT (тэтта).
  - **Хранилища**: SQLite (сессии/сообщения/оценки), ChromaDB (векторы), MinIO/S3 (отчёты/артефакты).
  - **Guardrails** (простая модерация) и **телеметрия** (лог событий).
  - **Отчёты**: PNG диаграмма навыков и JSON профиль для LMS.

## Точки API
- `POST /api/session/start` → `{session_id, first_question}`
- `POST /api/session/{id}/message` → `{reply, meta}`
- `GET  /api/session/{id}/report` → `{png_url, json_url}`
- `POST /api/session/{id}/complete` → `{ok:true}`
