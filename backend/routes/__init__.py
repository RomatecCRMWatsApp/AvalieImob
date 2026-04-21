# @module routes — Pacote de rotas FastAPI; importa todos os routers para registro no app
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.ptam import router as ptam_router
from routes.locacao import router as locacao_router
from routes.garantias import router as garantias_router
from routes.semoventes import router as semoventes_router
from routes.payments import router as payments_router
from routes.uploads import router as uploads_router
from routes.admin import router as admin_router
from routes.dashboard import router as dashboard_router
from routes.ai import router as ai_router
from routes.imoveis_crm import router as imoveis_crm_router
from routes.email import router as email_router
from routes.perfil_avaliador import router as perfil_avaliador_router
from routes.clients import router as clients_router
from routes.properties import router as properties_router
from routes.evaluations import router as evaluations_router
from routes.tvi import router as tvi_router

all_routers = [
    auth_router, users_router, ptam_router, locacao_router,
    garantias_router, semoventes_router, payments_router,
    uploads_router, admin_router, dashboard_router, ai_router,
    imoveis_crm_router, email_router, perfil_avaliador_router,
    clients_router, properties_router, evaluations_router,
    tvi_router,
]
