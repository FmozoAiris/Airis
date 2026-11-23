from odoo import fields, models


class CrmLeadBusinessLine(models.Model):
    _name = "crm.lead.business.line"
    _description = "Línea de negocio de la oportunidad"
    _order = "sequence, name"

    name = fields.Char(string="Línea", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class CrmLeadTypology(models.Model):
    _name = "crm.lead.typology"
    _description = "Tipología de producto de la oportunidad"
    _order = "sequence, name"

    name = fields.Char(string="Tipología", required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string="Color")
    active = fields.Boolean(default=True)
