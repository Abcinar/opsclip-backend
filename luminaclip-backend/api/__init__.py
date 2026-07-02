from fastapi import APIRouter
from .auth    import router as auth_router
from .videos  import router as videos_router
from .clips   import router as clips_router
from .credits import router as credits_router
from .admin   import router as admin_router

router = APIRouter()
router.include_router(auth_router,   prefix="/auth",    tags=["Auth"])
router.include_router(videos_router, prefix="/videos",  tags=["Videos"])
router.include_router(clips_router,  prefix="/clips",   tags=["Clips"])
router.include_router(credits_router,prefix="/credits", tags=["Credits"])
router.include_router(admin_router,  prefix="/admin",   tags=["Admin"])
