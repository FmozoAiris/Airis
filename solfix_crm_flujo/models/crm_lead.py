from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    is_review_stage = fields.Boolean(related="stage_id.is_review_stage")
    can_act_on_stage = fields.Boolean(
        string="Puede mover la etapa",
        compute="_compute_can_act_on_stage",
        help="El usuario actual puede enviar, aprobar o rechazar en la etapa actual.",
    )
    rejection_cause = fields.Text(
        string="Causa del rechazo",
        copy=False,
        help="La escribe el revisor antes de pulsar Rechazar. Mientras tenga texto "
        "no se puede aprobar.",
    )
    last_rejection = fields.Text(string="Último rechazo", readonly=True, copy=False)
    last_rejection_date = fields.Datetime(
        string="Fecha del último rechazo", readonly=True, copy=False
    )
    last_approval_date = fields.Datetime(
        string="Fecha de la última aprobación", readonly=True, copy=False
    )
    doc_approved_1 = fields.Boolean(
        string="Documentación aprobada (revisión 1)", readonly=True, copy=False, tracking=True
    )
    doc_approved_2 = fields.Boolean(
        string="Documentación aprobada (revisión 2)", readonly=True, copy=False, tracking=True
    )
    flow_log_ids = fields.One2many(
        "crm.lead.flow.log", "lead_id", string="Registro del flujo", readonly=True
    )
    rejection_count = fields.Integer(
        string="Rechazos", compute="_compute_rejection_count"
    )
    next_stage_is_won = fields.Boolean(
        string="La siguiente etapa es Ganado", compute="_compute_next_stage_is_won"
    )
    business_line_id = fields.Many2one(
        "crm.lead.business.line",
        string="Línea",
        tracking=True,
        help="Formato de la venta: venta, arrendamiento, mantenimiento…",
    )
    typology_ids = fields.Many2many(
        "crm.lead.typology",
        string="Tipología",
        help="Tipos de producto de la oportunidad: cámaras, pasos de peatones…",
    )

    @api.depends_context("uid")
    @api.depends("stage_id", "stage_id.is_review_stage", "stage_id.responsible_group_id")
    def _compute_can_act_on_stage(self):
        user = self.env.user
        is_admin = user.has_group("base.group_system")
        for lead in self:
            lead.can_act_on_stage = is_admin or lead.stage_id._flow_user_is_responsible(user)

    @api.depends("flow_log_ids.action")
    def _compute_rejection_count(self):
        for lead in self:
            lead.rejection_count = len(
                lead.flow_log_ids.filtered(lambda log: log.action == "reject")
            )

    @api.depends("stage_id", "team_id")
    def _compute_next_stage_is_won(self):
        for lead in self:
            stages = lead._flow_stages() if lead.stage_id else self.env["crm.stage"]
            ids = list(stages.ids)
            if lead.stage_id.id in ids and ids.index(lead.stage_id.id) + 1 < len(ids):
                lead.next_stage_is_won = stages[ids.index(lead.stage_id.id) + 1].is_won
            else:
                lead.next_stage_is_won = False

    def _flow_stages(self):
        self.ensure_one()
        return self.env["crm.stage"].search(
            ["|", ("team_ids", "in", self.team_id.ids), ("team_ids", "=", False)],
            order="sequence, id",
        )

    def _flow_check(self):
        self.ensure_one()
        if self.type != "opportunity":
            raise UserError(self.env._("Solo se pueden mover oportunidades."))
        if not self.active or self.won_status != "pending":
            raise UserError(self.env._("La oportunidad ya está ganada o perdida."))
        if not self.can_act_on_stage:
            raise UserError(
                self.env._(
                    "No tienes permiso para mover la oportunidad desde la etapa %s.",
                    self.stage_id.name,
                )
            )
        stages = self._flow_stages()
        if self.stage_id not in stages:
            raise UserError(
                self.env._("La etapa actual no pertenece al flujo del equipo de ventas.")
            )
        return stages

    def _flow_move(self, stages, step, action, cause=False):
        self.ensure_one()
        position = list(stages.ids).index(self.stage_id.id) + step
        if position < 0:
            raise UserError(self.env._("La oportunidad ya está en la primera etapa."))
        if position >= len(stages):
            raise UserError(self.env._("No hay una etapa siguiente."))
        origin, target = self.stage_id, stages[position]
        # Bypass the "stage is locked" check of write()
        self.with_context(solfix_flow_move=True).write({"stage_id": target.id})
        self.env["crm.lead.flow.log"].sudo().create(
            {
                "lead_id": self.id,
                "action": action,
                "stage_from_id": origin.id,
                "stage_to_id": target.id,
                "cause": cause,
                "user_id": self.env.user.id,
            }
        )
        return origin, target

    def _flow_check_requirements(self):
        self.ensure_one()
        stage = self.stage_id
        if stage.require_activities_done and self.activity_ids:
            raise UserError(
                self.env._(
                    "Completa las actividades pendientes antes de avanzar: %s",
                    ", ".join(self.activity_ids.mapped(lambda a: a.summary or a.activity_type_id.name)),
                )
            )
        if stage.require_attachment:
            count = self.env["ir.attachment"].sudo().search_count(
                [("res_model", "=", "crm.lead"), ("res_id", "=", self.id)]
            )
            if not count:
                raise UserError(
                    self.env._("Adjunta al menos un documento antes de avanzar desde %s.", stage.name)
                )

    def _flow_close_my_activities(self):
        self.ensure_one()
        mine = self.activity_ids.filtered(lambda a: a.user_id == self.env.user)
        if mine:
            mine.action_feedback(feedback=self.env._("Cerrada al mover la oportunidad con el flujo."))

    def _flow_entry_activity(self, stage):
        self.ensure_one()
        if not stage.entry_activity_type_id:
            return
        user = stage.entry_activity_user_id or self.user_id or self.env.user
        self.activity_schedule(
            activity_type_id=stage.entry_activity_type_id.id,
            summary=stage.entry_activity_type_id.summary or stage.entry_activity_type_id.name,
            user_id=user.id,
        )

    def action_flow_submit(self):
        for lead in self:
            stages = lead._flow_check()
            if lead.is_review_stage:
                raise UserError(
                    self.env._("En una etapa de revisión hay que aprobar o rechazar.")
                )
            lead._flow_check_requirements()
            origin, target = lead._flow_move(stages, 1, "submit")
            lead._flow_entry_activity(target)
            lead.message_post(
                body=self.env._(
                    "Enviado: %(origin)s → %(target)s",
                    origin=origin.name, target=target.name,
                )
            )
        return True

    def action_flow_approve(self):
        for lead in self:
            stages = lead._flow_check()
            if not lead.is_review_stage:
                raise UserError(self.env._("La etapa actual no es de revisión."))
            if (lead.rejection_cause or "").strip():
                raise UserError(
                    self.env._(
                        "Hay una causa de rechazo escrita. Bórrala para aprobar o pulsa Rechazar."
                    )
                )
            lead._flow_check_requirements()
            review_stages = stages.filtered("is_review_stage")
            review_number = list(review_stages.ids).index(lead.stage_id.id) + 1
            lead._flow_close_my_activities()
            origin, target = lead._flow_move(stages, 1, "approve")
            lead._flow_entry_activity(target)
            vals = {
                "last_rejection": False,
                "last_approval_date": fields.Datetime.now(),
            }
            if review_number == 1:
                vals["doc_approved_1"] = True
            elif review_number == 2:
                vals["doc_approved_2"] = True
            lead.write(vals)
            lead.message_post(
                body=self.env._(
                    "APROBADO en %(origin)s → %(target)s",
                    origin=origin.name, target=target.name,
                )
            )
        return True

    def action_flow_reject(self):
        for lead in self:
            stages = lead._flow_check()
            if not lead.is_review_stage:
                raise UserError(self.env._("La etapa actual no es de revisión."))
            cause = (lead.rejection_cause or "").strip()
            if not cause:
                raise UserError(
                    self.env._("Escribe la causa del rechazo antes de rechazar.")
                )
            lead._flow_close_my_activities()
            origin, target = lead._flow_move(stages, -1, "reject", cause=cause)
            fix_type = self.env.ref("solfix_crm_flujo.mail_activity_type_fix_errors", raise_if_not_found=False)
            lead.activity_schedule(
                activity_type_id=fix_type.id if fix_type else False,
                summary=self.env._("Subsanar errores"),
                note=cause,
                user_id=(lead.user_id or self.env.user).id,
                date_deadline=fields.Date.context_today(lead) + timedelta(days=1),
            )
            now = fields.Datetime.now()
            local_now = fields.Datetime.context_timestamp(lead, now)
            lead.write(
                {
                    "rejection_cause": False,
                    "last_rejection_date": now,
                    "last_rejection": self.env._(
                        "Rechazado en %(stage)s el %(date)s por %(user)s:\n%(cause)s",
                        stage=origin.name,
                        date=local_now.strftime("%d/%m/%Y %H:%M"),
                        user=self.env.user.name,
                        cause=cause,
                    ),
                }
            )
            lead.message_post(
                body=self.env._(
                    "RECHAZADO en %(origin)s → vuelve a %(target)s. Causa: %(cause)s",
                    origin=origin.name, target=target.name, cause=cause,
                )
            )
        return True

    def write(self, vals):
        if (
            "stage_id" in vals
            and not self.env.context.get("solfix_flow_move")
            and not self.env.su
            and not self.env.user.has_group("sales_team.group_sale_manager")
        ):
            moved = self.filtered(
                lambda lead: lead.type == "opportunity" and lead.stage_id.id != vals["stage_id"]
            )
            if moved:
                raise UserError(
                    self.env._(
                        "La etapa solo se puede cambiar con los botones del flujo "
                        "(Enviar a revisión, Aprobar, Rechazar)."
                    )
                )
        return super().write(vals)
