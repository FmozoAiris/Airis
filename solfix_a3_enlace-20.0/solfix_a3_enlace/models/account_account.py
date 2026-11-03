from odoo import fields, models

from .a3_format import fmt_account


class AccountAccount(models.Model):
    _inherit = "account.account"

    a3_code = fields.Char(
        string="Cuenta en A3",
        company_dependent=True,
        help="Subcuenta equivalente en A3. Vacío = código de Odoo completado "
        "con ceros a la derecha hasta los dígitos configurados.",
    )

    def _a3_get_code(self, company):
        self.ensure_one()
        account = self.with_company(company)
        return fmt_account(account.a3_code or account.code, company.a3_account_length or 8)
