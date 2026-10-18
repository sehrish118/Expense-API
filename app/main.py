from fastapi import FastAPI

from app.api.routers import auth
from app.core.exceptions import register_exception_handlers

app = FastAPI(title="Expense Tracker API", version="2.0.0")

register_exception_handlers(app)
app.include_router(auth.router)
