from fastapi import FastAPI

from wati_agent.mock_api.routes import broadcasts, contacts, messages, operators, tags, templates, tickets

app = FastAPI(title="Mock WATI API", version="0.1.0")

app.include_router(contacts.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(operators.router, prefix="/api/v1")
app.include_router(tags.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1")
app.include_router(broadcasts.router, prefix="/api/v1")
