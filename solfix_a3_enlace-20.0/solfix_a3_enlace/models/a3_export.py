import logging
import os

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.binary import BinaryBytes

from .a3_format import FILE_ENCODING

_logger = logging.getLogger(__name__)

FILE_NAME = "SUENLACE.DAT"


class A3Export(models.Model):
    _name = "a3.export"
    _description = "Exportación al enlace contable de A3"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char(
        string="Referencia", readonly=True, copy=False, default="/"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta", default=fields.Date.context_today)
    state = fields.Selection(
        [("draft", "Borrador"), ("done", "Generado")],
        default="draft",
        required=True,
        tracking=True,
    )
    move_ids = fields.One2many("account.move", "a3_export_id", string="Facturas")
    move_count = fields.Integer(compute="_compute_move_count", string="Nº facturas")
    record_count = fields.Integer(string="Nº registros", readonly=True)
    file_data = fields.Binary(string="Fichero", attachment=True, readonly=True, copy=False)
    file_name = fields.Char(default=FILE_NAME, readonly=True)
    written_path = fields.Char(string="Escrito en", readonly=True, copy=False)
    warnings = fields.Text(string="Avisos", readonly=True, copy=False)

    @api.depends("move_ids")
    def _compute_move_count(self):
        for export in self:
            export.move_count = len(export.move_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("a3.export") or "/"
        return super().create(vals_list)

    def _get_moves_domain(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("out_invoice", "out_refund", "in_invoice", "in_refund")),
            ("a3_export_id", "=", False),
        ]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))
        if self.company_id.a3_journal_ids:
            domain.append(("journal_id", "in", self.company_id.a3_journal_ids.ids))
        return domain

    def action_generate(self):
        for export in self:
            export._generate()
        return True

    def _generate(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("Esta exportación ya fue generada."))
        company = self.company_id
        if not company.a3_company_code:
            raise UserError(
                self.env._(
                    "Configura el 'Código de empresa A3' en la empresa %s.", company.name
                )
            )
        moves = self.env["account.move"].search(
            self._get_moves_domain(), order="date, move_type, name"
        )
        if not moves:
            raise UserError(self.env._("No hay facturas pendientes de exportar en ese rango."))

        lines, warnings, exported = [], [], self.env["account.move"]
        for move in moves:
            move_lines, move_warnings = move._a3_records()
            warnings += move_warnings
            if move_lines:
                lines += move_lines
                exported |= move
        if not lines:
            raise UserError("\n".join(warnings) or self.env._("Nada que exportar."))

        content = "".join(lines).encode(FILE_ENCODING, errors="replace")
        written_path = self._write_to_folder(content, warnings)
        exported.write({"a3_export_id": self.id})
        self.write(
            {
                "state": "done",
                "file_data": BinaryBytes(content, filename=FILE_NAME),
                "file_name": FILE_NAME,
                "record_count": len(lines),
                "written_path": written_path,
                "warnings": "\n".join(warnings) or False,
            }
        )
        self.message_post(
            body=self.env._(
                "Generado %(file)s con %(moves)s facturas y %(records)s registros.",
                file=FILE_NAME, moves=len(exported), records=len(lines),
            )
        )

    def _write_to_folder(self, content, warnings):
        path = (self.company_id.a3_export_path or "").strip()
        if not path:
            return False
        if not os.path.isdir(path):
            warnings.append(self.env._("La carpeta %s no existe: el fichero solo se adjuntó.", path))
            return False
        target = os.path.join(path, FILE_NAME)
        if os.path.exists(target):
            warnings.append(
                self.env._(
                    "Ya existe %s sin importar en A3: no se sobrescribió. "
                    "Descarga el fichero desde esta exportación.",
                    target,
                )
            )
            return False
        try:
            with open(target, "wb") as handle:
                handle.write(content)
        except OSError as error:
            warnings.append(self.env._("No se pudo escribir %(path)s: %(error)s", path=target, error=error))
            return False
        return target

    def action_reset(self):
        """Release the invoices so they can be exported again."""
        for export in self:
            export.move_ids.write({"a3_export_id": False})
            export.write(
                {"state": "draft", "file_data": False, "record_count": 0,
                 "written_path": False, "warnings": False}
            )
            export.message_post(body=self.env._("Exportación revertida: las facturas vuelven a estar pendientes."))
        return True

    def action_download(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(self.env._("No hay fichero generado."))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/a3.export/%s/file_data/%s?download=true" % (self.id, self.file_name),
            "target": "self",
        }

    def action_view_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Facturas exportadas"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("a3_export_id", "=", self.id)],
        }

    def unlink(self):
        if any(export.state == "done" for export in self):
            raise UserError(self.env._("Revierte la exportación antes de borrarla."))
        return super().unlink()

    @api.model
    def _cron_generate(self):
        """Daily export for every company with an A3 company code."""
        companies = self.env["res.company"].search([("a3_company_code", "!=", False)])
        for company in companies:
            export = self.create({"company_id": company.id, "date_from": False})
            try:
                with self.env.cr.savepoint():
                    export._generate()
            except UserError as error:
                _logger.info("A3 export for %s skipped: %s", company.name, error)
                export.unlink()
