from odoo import fields, models


class CrmStage(models.Model):
    _inherit = "crm.stage"

    is_review_stage = fields.Boolean(
        string="Etapa de revisión",
        help="En esta etapa el responsable aprueba (pasa a la siguiente etapa) o "
        "rechaza con una causa (vuelve a la etapa anterior).",
    )
    responsible_group_id = fields.Many2one(
        "res.groups",
        string="Grupo responsable",
        help="Usuarios que pueden mover la oportunidad desde esta etapa "
        "(enviar a revisión, aprobar o rechazar).\n"
        "Si se deja vacío: en etapas de revisión, Ventas / Administrador; "
        "en el resto, cualquier usuario de Ventas.",
    )
    require_activities_done = fields.Boolean(
        string="Exigir actividades hechas",
        help="No deja avanzar desde esta etapa mientras la oportunidad tenga "
        "actividades pendientes (p. ej. cargar documentos, licencias, contratos).",
    )
    require_attachment = fields.Boolean(
        string="Exigir documento adjunto",
        help="No deja avanzar desde esta etapa si la oportunidad no tiene al menos "
        "un documento adjunto.",
    )
    entry_activity_type_id = fields.Many2one(
        "mail.activity.type",
        string="Actividad al entrar",
        domain="['|', ('res_model', '=', False), ('res_model', '=', 'crm.lead')]",
        help="Actividad que se crea al llegar a esta etapa con los botones del flujo "
        "(p. ej. 'Revisar documentación' en Revisión 1).",
    )
    entry_activity_user_id = fields.Many2one(
        "res.users",
        string="Responsable de la actividad",
        help="A quién se asigna la actividad al entrar. Vacío: al comercial de la oportunidad.",
    )

    def _flow_user_is_responsible(self, user):
        if not self:
            return False
        self.ensure_one()
        if self.responsible_group_id:
            return self.responsible_group_id in user.all_group_ids
        default = (
            "sales_team.group_sale_manager" if self.is_review_stage
            else "sales_team.group_sale_salesman"
        )
        return user.has_group(default)
