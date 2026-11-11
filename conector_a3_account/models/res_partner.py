from odoo import fields, models

from .a3_format import fmt_account


class ResPartner(models.Model):
    _inherit = "res.partner"

    a3_customer_account = fields.Char(
        string="Subcuenta A3 cliente",
        company_dependent=True,
        help="Subcuenta del cliente en A3 (p. ej. 43000012). "
        "Vacío = prefijo de clientes + ID del contacto.",
    )
    a3_supplier_account = fields.Char(
        string="Subcuenta A3 proveedor",
        company_dependent=True,
        help="Subcuenta del proveedor en A3 (p. ej. 40000034). "
        "Vacío = prefijo de proveedores + ID del contacto.",
    )

    def _a3_get_account(self, company, kind):
        partner = self.commercial_partner_id.with_company(company)
        length = company.a3_account_length or 8
        explicit = (
            partner.a3_customer_account
            if kind == "customer"
            else partner.a3_supplier_account
        )
        if explicit:
            return fmt_account(explicit, length)
        prefix = (
            company.a3_customer_prefix if kind == "customer" else company.a3_supplier_prefix
        ) or ("430" if kind == "customer" else "400")
        suffix = str(partner.id).zfill(max(length - len(prefix), 1))
        return (prefix + suffix)[:12]
