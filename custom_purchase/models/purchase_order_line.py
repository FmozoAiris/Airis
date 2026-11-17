from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    inspection_attachment_ids = fields.Many2many(
        "ir.attachment",
        "purchase_order_line_inspection_rel",
        "line_id",
        "attachment_id",
        string="Documentos de inspección",
        copy=False,
        help="Informes de inspección y otros documentos de este producto en esta proforma.",
    )
    inspection_doc_count = fields.Integer(
        string="Docs. inspección", compute="_compute_inspection_doc_count"
    )

    @api.depends("inspection_attachment_ids")
    def _compute_inspection_doc_count(self):
        for line in self:
            line.inspection_doc_count = len(line.inspection_attachment_ids)

    def action_open_inspection_docs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Documentos de inspección"),
            "res_model": "purchase.order.line",
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (self.env.ref("custom_purchase.purchase_order_line_inspection_form").id, "form")
            ],
            "target": "new",
        }
