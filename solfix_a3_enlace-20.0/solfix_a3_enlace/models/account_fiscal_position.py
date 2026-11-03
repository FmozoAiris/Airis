from odoo import fields, models

A3_SUBTYPES_SALE = [
    ("01", "01 - Interior sujetas a IVA"),
    ("02", "02 - Exentas sin derecho a deducción"),
    ("03", "03 - Entregas intracomunitarias"),
    ("04", "04 - Intracomunitarias, operaciones triangulares"),
    ("05", "05 - Canarias, Ceuta y Melilla"),
    ("06", "06 - Exportaciones"),
    ("07", "07 - Otras operaciones no sujetas"),
    ("08", "08 - No sujetas o ISP con derecho a devolución"),
    ("09", "09 - Otras exentas con derecho a deducción"),
]
A3_SUBTYPES_PURCHASE = [
    ("01", "01 - Interior IVA deducible"),
    ("02", "02 - Compensaciones agrícolas"),
    ("03", "03 - Adquisiciones intracomunitarias"),
    ("04", "04 - Inversión del sujeto pasivo"),
    ("06", "06 - Importaciones"),
    ("07", "07 - IVA no deducible"),
]


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    a3_subtype_sale = fields.Selection(
        A3_SUBTYPES_SALE,
        string="Subtipo A3 (ventas)",
        help="Subtipo de factura expedida en A3. Vacío = 01.",
    )
    a3_subtype_purchase = fields.Selection(
        A3_SUBTYPES_PURCHASE,
        string="Subtipo A3 (compras)",
        help="Subtipo de factura recibida en A3. Vacío = 01.",
    )
