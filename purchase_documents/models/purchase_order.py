from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    factory_status = fields.Selection(
        selection_add=[("partial_transit", "Parcial, resto en tránsito"), ("partial",)],
        ondelete={"partial_transit": "set null"},
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
        super()._compute_factory_status()
        for order in self:
            if order.factory_status not in ("production", "partial"):
                continue
            open_receipts = order.picking_ids.filtered(
                lambda p: p.picking_type_code == "incoming"
                and p.state not in ("done", "cancel")
            )
            if any(open_receipts.mapped("shipment_departure_date")):
                order.factory_status = (
                    "partial_transit" if order.factory_status == "partial" else "transit"
                )
