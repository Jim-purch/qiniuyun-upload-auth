from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routes import auth_routes
from app.routes import token_routes
from app.routes import admin_routes


app = FastAPI(title="Qiniu Upload Auth Service")

# Routers
app.include_router(auth_routes.router)
app.include_router(token_routes.router)
app.include_router(admin_routes.router)

# Static & Templates (for admin UI later)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def root():
    return {"status": "ok", "service": "qiniuyun-upload-auth"}