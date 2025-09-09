```markdown
# AI-Tutor (скользящая диагностика)

## Быстрый старт (локально)

1. Скопируйте `.env.example` → `.env` и заполните `MISTRAL_API_KEY`. По умолчанию провайдер LLM — **Mistral**.
2. (Опционально) Для Яндекс: укажите `LLM_PROVIDER=yandex`, `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, `YANDEX_GPT_MODEL`, `YANDEX_EMBED_MODEL`.
3. Установите зависимости: `pip install -r requirements.txt`.
4. Инициализируйте хранилища:
   * `python -c "from backend.app.s3_client import ensure_bucket; ensure_bucket()"`
   * `python -c "from backend.app.rag.vectorstore import seed_if_empty; seed_if_empty()"`
5. Запустите бэкенд:  
   `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`
6. Запустите фронтенд:  
   `streamlit run frontend/streamlit_app.py`
7. Откройте `http://localhost:8501`.

## Через docker-compose

1. Создайте `.env` из `.env.example`.
2. `make up` или `docker compose up --build`.

## Что внутри

* **Streamlit** чат-клиент (очистка поля ввода при новом вопросе).
* **FastAPI** бэкенд с FSM/policy (режимы `exam` и `diagnostic`):
  * Многоагентный слой: `Tutor` (RAG на ChromaDB + LLM-роутер Mistral/Yandex), `Judge/Scorer` (JSON), `Bloom-Tagger`, `SOLO-Tagger`, `Planner`, `Summarizer`.
  * **Assessment Engine**: EMA + 2PL IRT (тэтта).
  * **Метрики**: Bloom & SOLO распределения, средний score, отчёты (PNG/JSON), эндпоинт `/api/session/{id}/metrics`.
  * **Auth**: регистрация/логин (JWT), список сессий пользователя `/api/me/sessions`, история сообщений `/api/session/{id}/messages`.
  * **Тестбенч**: `/api/testbench/run` и страницы в Streamlit.

## Точки API

* `POST /api/auth/register` → `{token}`
* `POST /api/auth/login` → `{token}`
* `GET  /api/me` → текущий пользователь
* `GET  /api/me/sessions` → список сессий пользователя
* `POST /api/session/start` → `{session_id, first_question}`
* `POST /api/session/{id}/message` → `{reply, meta}`
* `GET  /api/session/{id}/report` → `{png_url, json_url}`
* `GET  /api/session/{id}/messages` → история
* `GET  /api/session/{id}/metrics` → метрики Bloom/SOLO
* `POST /api/testbench/run` → запуск набора примеров

## Переключение на ЯндексGPT

В `.env`:

```

LLM\_PROVIDER=yandex
YANDEX\_API\_KEY=...
YANDEX\_FOLDER\_ID=...
YANDEX\_GPT\_MODEL=yandexgpt
YANDEX\_EMBED\_MODEL=text-search-query

```