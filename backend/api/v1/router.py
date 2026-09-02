from fastapi import APIRouter
from jwt_auth.admin_router import router as auth_router
from jwt_auth.portal_router import router as portal_login_router
from api.v1.system import router as system_router
from api.v1.sms import router as sms_router
from api.v1.portal import router as portal_router
from api.v1.chat import router as chat_router, portal_router as chat_portal_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(portal_login_router)
v1_router.include_router(system_router)
v1_router.include_router(sms_router)
v1_router.include_router(portal_router)
v1_router.include_router(chat_router)
v1_router.include_router(chat_portal_router)
