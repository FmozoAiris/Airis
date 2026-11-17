from odoo import api, fields, models

SHIPMENT_MODES = [
    ("air", "Avión"),
    ("sea", "Barco"),
    ("road", "Camión"),
    ("courier", "Mensajería"),
]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    shipment_mode = fields.Selection(SHIPMENT_MODES, string="Medio de transporte", tracking=True)
    shipment_carrier_id = fields.Many2one(
        "res.partner", string="Transitario / transportista", tracking=True
    )
    shipment_tracking_ref = fields.Char(
        string="Nº tracking / BL / AWB", copy=False, tracking=True
    )
    shipment_departure_date = fields.Date(
        string="Fecha de salida",
        copy=False,
        tracking=True,
        help="Al indicarla, este envío queda 'En tránsito' y el pedido de compra cambia de situación.",
    )
    shipment_eta = fields.Date(
        string="Llegada prevista (ETA)",
        copy=False,
        tracking=True,
        help="Fecha estimada de llegada de este envío. Es propia de cada recepción: "
        "a diferencia de la fecha programada, no se copia a las demás recepciones del mismo pedido.",
    )
    shipment_in_transit = fields.Boolean(
        string="En tránsito", compute="_compute_shipment_in_transit", store=True
    )

    @api.depends("shipment_departure_date", "state")
    def _compute_shipment_in_transit(self):
        for picking in self:
            picking.shipment_in_transit = bool(
                picking.shipment_departure_date and picking.state not in ("done", "cancel")
            )
