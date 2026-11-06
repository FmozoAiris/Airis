import os

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


def field(line, start, length):
    return line[start - 1 : start - 1 + length]


@tagged("post_install", "post_install_l10n", "-at_install")
class TestA3Export(AccountTestInvoicingCommon):
    _test_user_groups = None

    @classmethod
    @AccountTestInvoicingCommon.setup_country("es")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.write({"a3_company_code": "16", "a3_account_length": 8, "a3_export_format": "dat"})
        ref = cls.env["account.chart.template"].with_company(cls.company).ref
        cls.tax_s21 = ref("account_tax_template_s_iva21b")
        cls.tax_s10 = ref("account_tax_template_s_iva10b")
        cls.tax_p21 = ref("account_tax_template_p_iva21_bc")
        cls.tax_irpf = ref("account_tax_template_p_irpf15")
        cls.customer = cls.env["res.partner"].create({
            "name": "Ayuntamiento de Prueba",
            "vat": "ESA12345674",
            "zip": "28001",
            "country_id": cls.env.ref("base.es").id,
        })
        cls.supplier = cls.env["res.partner"].create({
            "name": "Proveedor Profesional",
            "vat": "ES47857909S",
            "zip": "08001",
            "country_id": cls.env.ref("base.es").id,
        })
        cls.customer.a3_customer_account = "43000099"

    def _invoice(self, move_type, partner, lines, ref=None):
        move = self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_date": "2026-10-15",
            "date": "2026-10-15",
            "ref": ref,
            "invoice_line_ids": [
                Command.create({"name": name, "quantity": 1, "price_unit": price, "tax_ids": [Command.set(taxes.ids)]})
                for name, price, taxes in lines
            ],
        })
        move.action_post()
        return move

    def _export(self):
        export = self.env["a3.export"].create({"company_id": self.company.id, "date_from": "2026-10-01", "date_to": "2026-10-31"})
        export.action_generate()
        content = export.file_data.content.decode("cp1252")
        records = content.split("\r\n")
        self.assertEqual(records[-1], "", "El fichero debe terminar en CRLF")
        return export, records[:-1]

    def test_sale_invoice_two_vat_rates(self):
        invoice = self._invoice("out_invoice", self.customer, [
            ("Caja normal", 1000.0, self.tax_s21),
            ("Mantenimiento", 500.0, self.tax_s10),
        ])
        export, records = self._export()
        self.assertEqual(len(records), 3)
        for record in records:
            self.assertEqual(len(record) + 2, 256)
            self.assertEqual(field(record, 1, 1), "4")
            self.assertEqual(field(record, 2, 5), "00016")
            self.assertEqual(field(record, 7, 8), "20261015")
            self.assertEqual(field(record, 253, 2), "EN")

        header, d1, d2 = records
        self.assertEqual(field(header, 15, 1), "1")
        self.assertEqual(field(header, 16, 12).strip(), "43000099")
        self.assertEqual(field(header, 58, 1), "1")
        self.assertEqual(field(header, 69, 1), "I")
        self.assertEqual(field(header, 100, 14), "+0000001760.00")
        self.assertEqual(field(header, 176, 14).strip(), "A12345674")
        self.assertEqual(field(header, 230, 5), "28001")
        self.assertEqual(field(header, 245, 8), "20261015")

        details = {field(r, 116, 5): r for r in (d1, d2)}
        d21, d10 = details["21.00"], details["10.00"]
        self.assertEqual(field(d21, 15, 1), "9")
        self.assertEqual(field(d21, 58, 1), "A")
        self.assertEqual(field(d21, 100, 2), "01")
        self.assertEqual(field(d21, 102, 14), "+0000001000.00")
        self.assertEqual(field(d21, 121, 14), "+0000000210.00")
        self.assertEqual(field(d10, 102, 14), "+0000000500.00")
        self.assertEqual(field(d10, 121, 14), "+0000000050.00")
        self.assertEqual(field(d21, 175, 1), "S")
        self.assertTrue(field(d21, 192, 12).strip().startswith("477"))
        self.assertEqual(len(field(d21, 16, 12).strip()), 8)
        self.assertEqual([field(d1, 69, 1), field(d2, 69, 1)], ["M", "U"])
        self.assertEqual(invoice.a3_export_id, export)
        self.assertTrue(invoice.a3_exported)

    def test_purchase_with_withholding(self):
        self._invoice("in_invoice", self.supplier, [
            ("Honorarios", 1000.0, self.tax_p21 | self.tax_irpf),
        ], ref="F-2026-0077")
        export, records = self._export()
        header, detail = records
        self.assertEqual(field(header, 58, 1), "2")
        self.assertTrue(field(header, 16, 12).strip().startswith("400"))
        self.assertEqual(field(header, 59, 10).strip(), "F260000077")
        self.assertEqual(field(header, 100, 14), "+0000001060.00")
        self.assertEqual(field(detail, 58, 1), "C")
        self.assertEqual(field(detail, 116, 5), "21.00")
        self.assertEqual(field(detail, 154, 5), "15.00")
        self.assertEqual(field(detail, 159, 14), "+0000000150.00")
        self.assertTrue(field(detail, 192, 12).strip().startswith("472"))
        self.assertTrue(field(detail, 216, 12).strip().startswith("4751"))

    def test_credit_note_and_no_double_export(self):
        self._invoice("out_refund", self.customer, [("Abono", 100.0, self.tax_s21)])
        export, records = self._export()
        self.assertEqual(field(records[0], 15, 1), "2")
        self.assertEqual(field(records[0], 100, 14), "+0000000121.00")
        with self.assertRaises(UserError):
            self._export()

    def test_invoice_and_refund_numbers_are_distinct(self):
        invoice = self._invoice("out_invoice", self.customer, [("Caja", 100.0, self.tax_s21)])
        refund = self._invoice("out_refund", self.customer, [("Abono", 100.0, self.tax_s21)])
        _export, records = self._export()
        headers = [r for r in records if field(r, 15, 1) in ("1", "2")]
        numbers = {field(r, 15, 1): field(r, 59, 10).strip() for r in headers}
        self.assertEqual(len(numbers), 2)
        self.assertNotEqual(numbers["1"], numbers["2"], (invoice.name, refund.name, numbers))
        for number in numbers.values():
            self.assertLessEqual(len(number), 10)

    def test_number_shortening(self):
        from ..models.a3_format import fmt_number

        self.assertEqual(fmt_number("INV/2026/00001"), "INV2600001")
        self.assertEqual(fmt_number("RINV/2026/00001"), "RINV260001")
        self.assertEqual(fmt_number("BILL/2026/10/0001"), "BILL261001")
        self.assertEqual(fmt_number("F-77"), "F-77")

    def test_reset_releases_invoices(self):
        invoice = self._invoice("out_invoice", self.customer, [("Caja", 100.0, self.tax_s21)])
        export, _records = self._export()
        with self.assertRaises(UserError):
            invoice.button_draft()
        export.action_reset()
        self.assertFalse(invoice.a3_export_id)
        self.assertEqual(export.state, "draft")
        export.action_generate()
        self.assertEqual(invoice.a3_export_id, export)

    def test_missing_company_code(self):
        self.company.a3_company_code = False
        self._invoice("out_invoice", self.customer, [("Caja", 100.0, self.tax_s21)])
        export = self.env["a3.export"].create({"company_id": self.company.id})
        with self.assertRaises(UserError):
            export.action_generate()

    def test_folder_check(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.company.a3_export_path = tmp
            action = self.company.action_a3_test_path()
            self.assertEqual(action["tag"], "display_notification")
            self.assertIn(tmp, action["params"]["message"])
            self.assertEqual(os.listdir(tmp), [])
        self.company.a3_export_path = "/no/existe/a3"
        with self.assertRaises(UserError):
            self.company.action_a3_test_path()
        self.company.a3_export_path = False
        with self.assertRaises(UserError):
            self.company.action_a3_test_path()

    def test_xlsx_customer_invoices(self):
        import io

        import openpyxl

        self.company.a3_export_format = "xlsx"
        categ_a = self.env["product.category"].create({"name": "CUOTAS CONTADORES"})
        product = self.env["product.product"].create({"name": "Cuota", "categ_id": categ_a.id})
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.customer.id,
            "invoice_date": "2026-10-15",
            "date": "2026-10-15",
            "invoice_line_ids": [
                Command.create({"product_id": product.id, "name": "Cuota", "quantity": 1,
                                "price_unit": 1000.0, "tax_ids": [Command.set(self.tax_s21.ids)]}),
                Command.create({"name": "Mantenimiento", "quantity": 1, "price_unit": 500.0,
                                "tax_ids": [Command.set(self.tax_s10.ids)]}),
            ],
        })
        invoice.action_post()
        refund = self._invoice("out_refund", self.customer, [("Abono", 100.0, self.tax_s21)])
        self._invoice("in_invoice", self.supplier, [("Compra", 50.0, self.tax_p21)])

        export = self.env["a3.export"].create(
            {"company_id": self.company.id, "date_from": "2026-10-01", "date_to": "2026-10-31"}
        )
        export.action_generate()
        self.assertTrue(export.file_name.endswith(".xlsx"))
        sheet = openpyxl.load_workbook(io.BytesIO(export.file_data.content)).active
        rows = list(sheet.iter_rows(values_only=True))
        self.assertEqual(len(rows), 3, "2 filas de la factura (21 y 10 %) + 1 del abono; sin compras")
        self.assertTrue(all(len(r) == 27 for r in rows))
        by_number = {}
        for row in rows:
            by_number.setdefault(row[1], []).append(row)
        inv_rows = {r[15]: r for r in by_number[invoice.name]}
        r21, r10 = inv_rows[21], inv_rows[10]
        self.assertEqual(r21[4], "A12345674")           
        self.assertEqual(r21[6], "T")                  
        self.assertEqual(r21[7], 1760)                  
        self.assertEqual(r21[8], 1500)                  
        self.assertEqual((r21[9], r21[10], r21[11]), (0, 500, 1000))  
        self.assertEqual(r21[13], "CUOTAS CONTADORES")  
        self.assertEqual(len(str(r21[14])), 8)          
        self.assertEqual((r21[17], r21[18]), (1000, 210))   
        self.assertEqual((r10[17], r10[18]), (500, 50))
        self.assertEqual(r21[22], 1)                    
        self.assertEqual(r21[25], "ESPAÑA")           
        ref_row = by_number[refund.name][0]
        self.assertEqual(ref_row[6], "N")
        self.assertEqual(ref_row[7], 121)
        self.assertEqual((ref_row[17], ref_row[18]), (-100, -21))
        self.assertTrue(refund.a3_export_id)
