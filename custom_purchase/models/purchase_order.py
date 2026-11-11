from odoo import api, fields, models

FACTORY_STATUS = [
    ("requested", "Solicitado"),
    ("production", "En producción"),
    ("transit", "En tránsito"),
    ("partial", "Recibido parcial"),
    ("received", "Recibido"),
    ("cancel", "Cancelado"),
]


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    proforma_date = fields.Date(string="Fecha proforma", copy=False, tracking=True)
    production_date = fields.Date(
        string="Fecha estimada de producción", copy=False, tracking=True
    )
    departure_date = fields.Date(
        string="Fecha de salida de fábrica",
        copy=False,
        tracking=True,
        help="Al indicarla, el pedido pasa a 'En tránsito'.",
    )
    factory_status = fields.Selection(
        FACTORY_STATUS,
        string="Situación",
        compute="_compute_factory_status",
        store=True,
        tracking=True,
        group_expand=True,
        help="Solicitado: sin proforma (presupuesto).\n"
        "En producción: proforma recibida y pedido confirmado.\n"
        "En tránsito: con fecha de salida de fábrica.\n"
        "Recibido parcial / Recibido: según las recepciones validadas.",
    )

    @api.depends("state", "receipt_status", "departure_date")
    def _compute_factory_status(self):
        for order in self:
            if order.state == "cancel":
                status = "cancel"
            elif order.state in ("draft", "sent", "to approve"):
                status = "requested"
            elif order.receipt_status == "full":
                status = "received"
            elif order.receipt_status == "partial":
                status = "partial"
            elif order.departure_date:
                status = "transit"
            else:
                status = "production"
            order.factory_status = status
