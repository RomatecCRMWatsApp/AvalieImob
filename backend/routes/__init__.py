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
from routes.maps import router as maps_router
from routes.cnd import router as cnd_router
from routes.scraper import router as scraper_router
from routes.search import router as search_router
from routes.assinatura import router as assinatura_router
from routes.samples import router as samples_router
from routes.cub import router as cub_router
from routes.sigef import router as sigef_router
from routes.zonas import router as zonas_router
from routes.contratos import router as contratos_router

all_routers = [
    auth_router, users_router, ptam_router, locacao_router,
    garantias_router, semoventes_router, payments_router,
    uploads_router, admin_router, dashboard_router, ai_router,
    imoveis_crm_router, email_router, perfil_avaliador_router,
    clients_router, properties_router, evaluations_router,
    tvi_router, maps_router, cnd_router, scraper_router,
    cnd_router, scraper_router, search_router, assinatura_router, samples_router, cub_router,
    sigef_router, zonas_router, contratos_router,
]
