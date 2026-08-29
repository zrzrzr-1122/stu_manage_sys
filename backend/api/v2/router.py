from fastapi import APIRouter

from api.v2.students import router as students_router
from api.v2.classes import router as classes_router
from api.v2.teachers import router as teachers_router
from api.v2.scores import router as scores_router
from api.v2.employments import router as employments_router
from api.v2.departments import router as departments_router
from api.v2.consultants import router as consultants_router

v2_router = APIRouter(prefix="/api/v2")
v2_router.include_router(students_router)
v2_router.include_router(classes_router)
v2_router.include_router(teachers_router)
v2_router.include_router(scores_router)
v2_router.include_router(employments_router)
v2_router.include_router(departments_router)
v2_router.include_router(consultants_router)
