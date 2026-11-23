{
    "name": "Solfix - Flujo de revisión en CRM",
    "summary": "Flujo de oportunidades con etapas de revisión: enviar a revisión, "
    "aprobar o rechazar con causa, registro del flujo, requisitos por etapa, "
    "línea y tipología, y bloqueo del cambio libre de etapa",
    "version": "20.0.1.1.0",
    "category": "Sales/CRM",
    "author": "Solfix FM",
    "license": "LGPL-3",
    "depends": ["crm"],
    "data": [
        "security/ir.access.csv",
        "data/crm_flujo_data.xml",
        "views/crm_stage_views.xml",
        "views/crm_classification_views.xml",
        "views/crm_lead_views.xml",
    ],
    "installable": True,
    "application": False,
}
