{
    "name": "Enlace contable a3ASESOR (SUENLACE.DAT)",
    "summary": "Exporta facturas de venta y compra de Odoo al fichero "
    "SUENLACE.DAT del enlace contable de a3ASESOR | con",
    "version": "20.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Solfix",
    "license": "LGPL-3",
    "depends": ["account", "l10n_es"],
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
