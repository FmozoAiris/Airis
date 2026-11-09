from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round

from .a3_format import (
    A3Record,
    fmt_amount,
    fmt_number,
    fmt_rate,
    fmt_vat,
)

VAT_TYPES = {
    "sujeto",
    "sujeto_agricultura",
    "sujeto_isp",
    "no_sujeto",
    "no_sujeto_loc",
    "no_deducible",
    "exento",
    "dua",
}
SUBJECT_TYPES = {"sujeto", "sujeto_agricultura", "sujeto_isp", "no_deducible", "dua"}


class AccountMove(models.Model):
    _inherit = "account.move"

    a3_export_id = fields.Many2one(
        "a3.export",
        string="Exportación A3",
        copy=False,
        readonly=True,
        index="btree_not_null",
    )
    a3_exported = fields.Boolean(
        string="Exportada a A3", compute="_compute_a3_exported", store=True
    )

    @api.depends("a3_export_id")
    def _compute_a3_exported(self):
        for move in self:
            move.a3_exported = bool(move.a3_export_id)

    def button_draft(self):
        exported = self.filtered("a3_export_id")
        if exported and not self.env.context.get("a3_force_draft"):
            raise UserError(
                self.env._(
                    "Estas facturas ya se exportaron a A3 (%(exports)s). "
                    "Revierte primero la exportación o corrige el asiento en A3.",
                    exports=", ".join(exported.a3_export_id.mapped("name")),
                )
            )
        return super().button_draft()

    def _a3_classify_taxes(self, taxes):
        vat = rec = ret = self.env["account.tax"]
        for tax in taxes.flatten_taxes_hierarchy():
            es_type = getattr(tax, "l10n_es_type", False)
            if es_type == "ignore":
                continue
            if es_type == "retencion" or (not es_type and tax.amount < 0):
                ret |= tax
            elif es_type == "recargo":
                rec |= tax
            elif es_type in VAT_TYPES or not es_type:
                vat |= tax
        return vat[:1], rec[:1], ret[:1]

    def _a3_tax_amounts(self):
        self.ensure_one()
        amounts, accounts = {}, {}
        for line in self.line_ids.filtered("tax_line_id"):
            if (line.tax_repartition_line_id.factor_percent or 0.0) <= 0:
                # e.g. the self-assessed (negative) side of a reverse charge
                continue
            tax = line.tax_line_id
            amounts[tax] = amounts.get(tax, 0.0) + abs(line.balance)
            accounts.setdefault(tax, line.account_id)
        return amounts, accounts

    def _a3_detail_groups(self):
        self.ensure_one()
        company = self.company_id
        groups = {}
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
            vat, rec, ret = self._a3_classify_taxes(line.tax_ids)
            key = (line.account_id, vat, rec, ret)
            group = groups.setdefault(
                key,
                {
                    "account": line.account_id,
                    "vat": vat,
                    "rec": rec,
                    "ret": ret,
                    "base": 0.0,
                    "vat_amount": 0.0,
                    "rec_amount": 0.0,
                    "ret_amount": 0.0,
                    "label": line.name or line.product_id.display_name or "",
                },
            )
            group["base"] += abs(line.balance)

        tax_amounts, tax_accounts = self._a3_tax_amounts()
        groups = list(groups.values())
        for field, amount_key in (("vat", "vat_amount"), ("rec", "rec_amount"), ("ret", "ret_amount")):
            for tax in {g[field] for g in groups if g[field]}:
                members = [g for g in groups if g[field] == tax]
                total_base = sum(g["base"] for g in members)
                total_tax = tax_amounts.get(tax, 0.0)
                distributed = 0.0
                for index, group in enumerate(members):
                    if index == len(members) - 1:
                        share = total_tax - distributed
                    else:
                        share = float_round(
                            total_tax * group["base"] / total_base if total_base else 0.0,
                            precision_rounding=company.currency_id.rounding,
                        )
                    group[amount_key] = share
                    distributed += share
        for group in groups:
            for field in ("vat", "rec", "ret"):
                tax = group[field]
                group[field + "_account"] = (
                    tax_accounts[tax]._a3_get_code(company) if tax and tax in tax_accounts else ""
                )
        return groups

    def _a3_subtype(self):
        fpos = self.fiscal_position_id
        if self.is_sale_document(include_receipts=True):
            return fpos.a3_subtype_sale or "01"
        return fpos.a3_subtype_purchase or "01"

    def _a3_records(self):
        self.ensure_one()
        company = self.company_id
        warnings = []
        is_sale = self.is_sale_document(include_receipts=True)
        is_refund = self.move_type in ("out_refund", "in_refund")
        partner = self.commercial_partner_id
        partner_account = partner._a3_get_account(company, "customer" if is_sale else "supplier")
        number = fmt_number(self.name if is_sale else (self.ref or self.name))
        entry_date = self.date
        invoice_date = self.invoice_date or self.date
        description = (partner.name or "")[:30]

        groups = self._a3_detail_groups()
        if not groups:
            return [], [self.env._("%s: sin líneas de producto, no se exporta.", self.name)]

        total = sum(g["base"] + g["vat_amount"] + g["rec_amount"] - g["ret_amount"] for g in groups)
        if abs(total - abs(self.amount_total_signed)) > 0.01:
            warnings.append(
                self.env._(
                    "%(move)s: el total exportado (%(exported).2f) no coincide con el total "
                    "de la factura (%(total).2f). Revísala en A3.",
                    move=self.name, exported=total, total=abs(self.amount_total_signed),
                )
            )

        lines = []
        header = A3Record(company.a3_company_code, entry_date, "2" if is_refund else "1")
        header.set(16, 12, partner_account)
        header.set(28, 30, partner.name)
        header.set(58, 1, "1" if is_sale else "2")
        header.set(59, 10, number)
        header.set(69, 1, "I")
        header.set(70, 30, description)
        header.set(100, 14, fmt_amount(total))
        vat = fmt_vat(partner.vat)
        if vat:
            header.set(176, 14, vat)
            header.set(190, 40, partner.name)
            header.set(230, 5, (partner.zip or "")[:5])
        header.set(237, 8, invoice_date.strftime("%Y%m%d"))
        header.set(245, 8, invoice_date.strftime("%Y%m%d"))
        lines.append(header.render())

        subtype = self._a3_subtype()
        for index, group in enumerate(groups):
            detail = A3Record(company.a3_company_code, entry_date, "9")
            detail.set(16, 12, group["account"]._a3_get_code(company))
            detail.set(28, 30, group["account"].name)
            # Base: sales are credited (A = abono), purchases debited (C = cargo)
            detail.set(58, 1, "A" if is_sale else "C")
            detail.set(59, 10, number)
            detail.set(69, 1, "U" if index == len(groups) - 1 else "M")
            detail.set(70, 30, group["label"])
            detail.set(100, 2, subtype)
            detail.set(102, 14, fmt_amount(group["base"]))
            detail.set(116, 5, fmt_rate(group["vat"].amount if group["vat"] else 0.0))
            detail.set(121, 14, fmt_amount(group["vat_amount"]))
            detail.set(135, 5, fmt_rate(group["rec"].amount if group["rec"] else 0.0))
            detail.set(140, 14, fmt_amount(group["rec_amount"]))
            detail.set(154, 5, fmt_rate(group["ret"].amount if group["ret"] else 0.0))
            detail.set(159, 14, fmt_amount(group["ret_amount"]))
            es_type = getattr(group["vat"], "l10n_es_type", False) if group["vat"] else False
            subject = bool(group["vat_amount"] or group["rec_amount"] or group["ret_amount"]) or (
                es_type in SUBJECT_TYPES
            )
            detail.set(175, 1, "S" if subject else "N")
            detail.set(192, 12, group["vat_account"])
            detail.set(204, 12, group["rec_account"])
            detail.set(216, 12, group["ret_account"])
            lines.append(detail.render())
        return lines, warnings
