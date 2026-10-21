from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import config
from db import init_db
from middleware import log_failed_requests
from routes.auth import router as auth_router
from routes.me import router as me_router
from routes.holidays import router as holidays_router, admin_router as admin_holidays_router
from routes.gameplay import router as gameplay_router
from routes.shop import router as shop_router
from routes.rewards import router as rewards_router, admin_router as admin_rewards_router
from routes.stats import admin_router as admin_stats_router
from routes.players import admin_router as admin_players_router
from routes.appearance import router as appearance_router, admin_router as admin_appearance_router
from routes.logs import admin_router as admin_logs_router
from routes.settings import admin_router as admin_settings_router

init_db()


app = FastAPI(title="Holidays API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5176", "https://vk.com", "https://m.vk.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(BaseHTTPMiddleware, dispatch=log_failed_requests)

app.mount("/api/uploads", StaticFiles(directory=config.UPLOADS_DIR), name="uploads")

app.include_router(auth_router)
app.include_router(me_router)
app.include_router(holidays_router)
app.include_router(admin_holidays_router)
app.include_router(gameplay_router)
app.include_router(shop_router)
app.include_router(rewards_router)
app.include_router(admin_rewards_router)
app.include_router(admin_stats_router)
app.include_router(admin_players_router)
app.include_router(appearance_router)
app.include_router(admin_appearance_router)
app.include_router(admin_logs_router)
app.include_router(admin_settings_router)


@app.get("/api/")
def health():
    return {"status": "ok", "service": "holidays-api"}
