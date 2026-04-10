"""Route and middleware registration helpers (stage-3)."""

from typing import Callable, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def register_all_routes(
    app: FastAPI,
    *,
    auth_router: Any,
    unified_auth_router: Any,
    unified_login_router: Any,
    doctor_router: Any,
    admin_router: Any,
    prescription_router: Any,
    prescription_ai_router: Any,
    payment_router: Any,
    decoction_router: Any,
    decision_tree_router: Any,
    decision_tree_data_router: Any,
    symptom_analysis_router: Any,
    review_router: Any,
    unified_consultation_router: Any,
    database_management_router: Any,
    conversation_sync_router: Any,
    user_data_sync_router: Any,
    data_migration_router: Any,
    user_sessions_router: Any,
    medical_knowledge_router: Any,
    follow_up_router: Any,
    session_router: Any,
    security_router: Any,
    decision_tree_usage_router: Any,
    prescription_review_router: Any,
    prescription_structured_edit_router: Any,
    mindmap_router: Any,
    websocket_sync_router: Any,
    conversation_management_router: Any,
) -> None:
    """Register all API routers in legacy order to keep behavior stable."""
    app.include_router(auth_router)
    app.include_router(unified_auth_router)
    app.include_router(unified_login_router)
    app.include_router(doctor_router)
    app.include_router(admin_router)
    app.include_router(prescription_router)
    app.include_router(prescription_ai_router)
    app.include_router(payment_router)
    app.include_router(decoction_router)
    app.include_router(decision_tree_router)
    app.include_router(decision_tree_data_router)
    app.include_router(symptom_analysis_router)
    app.include_router(review_router)
    app.include_router(unified_consultation_router)
    app.include_router(database_management_router)
    app.include_router(conversation_sync_router)
    app.include_router(user_data_sync_router)
    app.include_router(data_migration_router)
    app.include_router(user_sessions_router)
    app.include_router(medical_knowledge_router)
    app.include_router(follow_up_router)
    app.include_router(session_router)
    app.include_router(security_router)
    app.include_router(decision_tree_usage_router)
    app.include_router(prescription_review_router)
    app.include_router(prescription_structured_edit_router)
    app.include_router(mindmap_router)
    app.include_router(websocket_sync_router)
    app.include_router(conversation_management_router, prefix="/api", tags=["conversation"])


def setup_exception_and_security(
    app: FastAPI,
    security_available: bool,
    protect_api_routes: Callable[[FastAPI], None],
) -> None:
    """Apply global exception handlers and optionally protect routes."""
    from api.middleware.exception_handler import setup_exception_handlers

    setup_exception_handlers(app)
    if security_available:
        protect_api_routes(app)


def setup_cors_middleware(app: FastAPI) -> None:
    """Keep current CORS behavior unchanged."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://mxh0510.cn",
            "https://www.mxh0510.cn",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost",
            "http://127.0.0.1",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

