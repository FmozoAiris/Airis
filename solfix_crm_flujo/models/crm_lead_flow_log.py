from odoo import fields, models


class CrmLeadFlowLog(models.Model):
    _name = "crm.lead.flow.log"
    _description = "Registro del flujo de la oportunidad"
    _order = "date desc, id desc"

    lead_id = fields.Many2one(
        "crm.lead", string="Oportunidad", required=True, index=True, ondelete="cascade"
    )
    date = fields.Datetime(string="Fecha", required=True, default=fields.Datetime.now)
    user_id = fields.Many2one(
        "res.users", string="Usuario", required=True, default=lambda self: self.env.user
    )
    action = fields.Selection(
        [
            ("submit", "Enviado a revisión"),
            ("approve", "Aprobado"),
            ("reject", "Rechazado"),
        ],
        string="Acción",
        required=True,
    )
    stage_from_id = fields.Many2one("crm.stage", string="De etapa")
    stage_to_id = fields.Many2one("crm.stage", string="A etapa")
    cause = fields.Text(string="Causa del rechazo")
