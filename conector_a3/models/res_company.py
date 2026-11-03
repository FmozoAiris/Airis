from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    a3_company_code = fields.Char(
        string="Código de empresa A3",
        size=5,
        help="Código de la empresa en a3ASESOR | con (5 dígitos, p. ej. 00016).",
    )
    a3_account_length = fields.Integer(
        string="Dígitos de subcuenta A3",
        default=8,
        help="Longitud de las subcuentas en A3. Las cuentas de Odoo se "
        "completan con ceros a la derecha hasta esta longitud.",
    )
    a3_customer_prefix = fields.Char(
        string="Prefijo subcuentas de clientes", default="430"
    )
    a3_supplier_prefix = fields.Char(
        string="Prefijo subcuentas de proveedores", default="400"
    )
    a3_journal_ids = fields.Many2many(
        "account.journal",
        "a3_company_journal_rel",
        "company_id",
        "journal_id",
        string="Diarios a exportar a A3",
        domain="[('type', 'in', ('sale', 'purchase')), ('company_id', '=', id)]",
        help="Vacío = todos los diarios de ventas y compras.",
    )
    a3_export_path = fields.Char(
        string="Carpeta de destino del enlace",
        help="Ruta en el servidor de Odoo donde se dejará SUENLACE.DAT "
        "(p. ej. una carpeta compartida con el servidor de A3). "
        "Vacío = solo se adjunta a la exportación para descargarlo.",
    )

    @api.constrains("a3_company_code")
    def _check_a3_company_code(self):
        for company in self:
            code = company.a3_company_code
            if code and (not code.isdigit() or len(code) > 5):
                raise ValidationError(
                    self.env._("El código de empresa A3 debe tener hasta 5 dígitos.")
                )

    @api.constrains("a3_account_length")
    def _check_a3_account_length(self):
        for company in self:
            if not 6 <= company.a3_account_length <= 12:
                raise ValidationError(
                    self.env._("Los dígitos de subcuenta A3 deben estar entre 6 y 12.")
                )
