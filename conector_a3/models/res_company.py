import os
import time

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

TEST_PREFIX = "odoo_prueba_conexion_"


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
    a3_export_format = fields.Selection(
        [
            ("xlsx", "Excel (importación de facturas expedidas)"),
            ("dat", "SUENLACE.DAT (enlace contable)"),
        ],
        string="Formato del fichero",
        default="xlsx",
        required=True,
        help="Excel: hoja con una fila por factura, familia y tipo de IVA, para la "
        "importación de facturas expedidas de A3 (misma plantilla que se usaba con Aqua). "
        "SUENLACE.DAT: fichero del enlace contable (ventas y compras).",
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

    @staticmethod
    def _a3_find_mount(path):
        """Return (mount_point, fstype, source) of the mount holding ``path``."""
        best = ("/", "", "")
        try:
            with open("/proc/mounts", encoding="utf-8") as handle:
                for line in handle:
                    parts = line.split()
                    if len(parts) < 3:
                        continue
                    source, mount_point, fstype = parts[0], parts[1], parts[2]
                    mount_point = mount_point.replace("\\040", " ")
                    if (path == mount_point or path.startswith(mount_point.rstrip("/") + "/")) and len(
                        mount_point
                    ) >= len(best[0]):
                        best = (mount_point, fstype, source)
        except OSError:
            pass
        return best

    def action_a3_test_path(self):
        self.ensure_one()
        _ = self.env._
        path = (self.a3_export_path or "").strip()
        if not path:
            raise UserError(_("Indica primero la carpeta de destino del enlace."))
        if not os.path.isdir(path):
            raise UserError(
                _(
                    "La carpeta %s no existe dentro del servidor de Odoo. "
                    "Revisa que el volumen del share de A3 esté montado en esa ruta.",
                    path,
                )
            )
        mount_point, fstype, source = self._a3_find_mount(os.path.realpath(path))
        target = os.path.join(path, "%s%s.txt" % (TEST_PREFIX, int(time.time())))
        payload = ("Prueba de escritura desde Odoo (%s)\r\n" % self.name).encode("cp1252", "replace")
        try:
            with open(target, "wb") as handle:
                handle.write(payload)
            with open(target, "rb") as handle:
                read_back = handle.read()
            os.remove(target)
        except OSError as error:
            raise UserError(
                _(
                    "No se pudo escribir en %(path)s: %(error)s. "
                    "Revisa el rol de la identidad sobre el share y que el volumen no esté en solo lectura.",
                    path=path, error=error,
                )
            ) from error
        if read_back != payload:
            raise UserError(_("El fichero de prueba se leyó distinto de como se escribió en %s.", path))

        lines = [
            _("Escritura, lectura y borrado correctos en %s.", path),
            _("Montaje: %(mount)s (tipo %(fstype)s, origen %(origin)s).",
              mount=mount_point, fstype=fstype or "?", origin=source or "?"),
        ]
        notif_type = "success"
        if fstype not in ("cifs", "smb3", "smbfs", "nfs", "nfs4"):
            notif_type = "warning"
            lines.append(
                _(
                    "Atención: la carpeta no está en un volumen de red (tipo %s). "
                    "Lo que se escriba aquí no llegará al share de A3 y se perderá al reiniciar el contenedor.",
                    fstype or "?",
                )
            )
        pending = os.path.join(path, "SUENLACE.DAT")
        if os.path.exists(pending):
            lines.append(_("Hay un SUENLACE.DAT pendiente de importar en A3."))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Carpeta de enlace A3"),
                "message": "\n".join(lines),
                "type": notif_type,
                "sticky": True,
            },
        }
