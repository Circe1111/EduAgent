from fastapi import APIRouter

router = APIRouter()

from app.api.v1.chat import router as chat_router
from app.api.v1.resources import router as resources_router
from app.api.v1.profile import router as profile_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.monitor import router as monitor_router
from app.api.v1.auth import router as auth_router
from app.api.v1.study import router as study_router
from app.api.v1.quiz import router as quiz_router
from app.api.v1.favorite import router as favorite_router
from app.api.v1.badge import router as badge_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.settings import router as settings_router

router.include_router(chat_router)
router.include_router(resources_router)
router.include_router(profile_router)
router.include_router(feedback_router)
router.include_router(monitor_router)
router.include_router(auth_router)
router.include_router(study_router)
router.include_router(quiz_router)
router.include_router(favorite_router)
router.include_router(badge_router)
router.include_router(prompts_router)
router.include_router(settings_router)
