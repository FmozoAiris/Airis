from odoo import api, fields, models

FACTORY_STATUS = [
    ("requested", "Solicitado"),
    ("production", "En producción"),
    ("transit", "En tránsito"),
    ("partial_transit", "Parcial, resto en tránsito"),
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
        help="Fecha general de salida del pedido. Si el pedido va en varios envíos, "
        "indique la salida, el tracking y la llegada prevista en cada recepción.",
    )
    factory_status = fields.Selection(
        FACTORY_STATUS,
        string="Situación",
        compute="_compute_factory_status",
        store=True,
        tracking=True,
        group_expand=True,
        help="Solicitado: presupuesto sin confirmar.\n"
        "En producción: pedido confirmado, sin envío en camino.\n"
        "En tránsito: algún envío tiene fecha de salida y aún no se ha recibido nada.\n"
        "Parcial, resto en tránsito: ya se recibió una parte y lo pendiente va en camino.\n"
        "Recibido parcial: se recibió una parte y lo pendiente sigue en fábrica.\n"
        "Recibido: todo recibido.",
    )
    shipment_picking_ids = fields.Many2many(
        "stock.picking",
        string="Envíos",
        compute="_compute_shipment_picking_ids",
    )

    @api.depends("picking_ids")
    def _compute_shipment_picking_ids(self):
        for order in self:
            order.shipment_picking_ids = order.picking_ids.filtered(
                lambda p: p.picking_type_code == "incoming"
            )

    @api.depends(
        "state",
        "receipt_status",
        "departure_date",
        "picking_ids.state",
        "picking_ids.shipment_departure_date",
    )
    def _compute_factory_status(self):
        for order in self:
            open_receipts = order.picking_ids.filtered(
                lambda p: p.picking_type_code == "incoming"
                and p.state not in ("done", "cancel")
            )
            in_transit = any(open_receipts.mapped("shipment_departure_date"))
            if order.state == "cancel":
                status = "cancel"
            elif order.state in ("draft", "sent", "to approve"):
                status = "requested"
            elif order.receipt_status == "full":
                status = "received"
            elif order.receipt_status == "partial":
                status = "partial_transit" if in_transit else "partial"
            elif in_transit or order.departure_date:
                status = "transit"
            else:
                status = "production"
            order.factory_status = status
