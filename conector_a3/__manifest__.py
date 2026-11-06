{
    "name": "Enlace contable a3ASESOR (SUENLACE.DAT)",
    "summary": "Exporta facturas de Odoo a a3ASESOR | con: Excel de facturas "
    "expedidas o fichero SUENLACE.DAT del enlace contable",
    "version": "20.0.1.2.0",
    "category": "Accounting/Accounting",
    "author": "Solfix FM",
    "license": "LGPL-3",
    "depends": ["account", "l10n_es"],
    "external_dependencies": {"python": ["openpyxl"]},
    "data": [
        "security/ir.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/a3_export_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/account_views.xml",
    ],
    "installable": True,
    "application": False,
}
