=========================================
Enlace contable a3ASESOR (SUENLACE.DAT)
=========================================

Genera desde Odoo el fichero ``SUENLACE.DAT`` del *enlace contable de entrada*
de a3ASESOR | con, con las facturas de venta, compra y rectificativas validadas.

Registros generados (formato de 256 posiciones de Wolters Kluwer):

* Tipo ``1`` / ``2``: cabecera de factura / rectificativa (subcuenta del
  cliente o proveedor, NIF, total, fechas).
* Tipo ``9``: detalle por cuenta y tipo de IVA (base, IVA, recargo de
  equivalencia, retención, cuentas de impuestos, subtipo de factura).

Configuración
=============

1. Empresa → pestaña *Enlace A3*: código de empresa A3 (5 dígitos), dígitos de
   subcuenta, prefijos de clientes/proveedores, diarios y carpeta de destino.
2. Contactos → pestaña *Facturación*: subcuenta A3 de cliente/proveedor
   (opcional; si se deja vacía se usa prefijo + ID del contacto).
3. Plan contable: campo *Cuenta en A3* si la equivalencia no es el código de
   Odoo completado con ceros.
4. Posiciones fiscales: subtipo A3 de ventas/compras (intracomunitarias,
   exportaciones, ISP...). Vacío = 01.

Uso
===

Contabilidad → *Exportación A3* → Nuevo → rango de fechas → *Generar
SUENLACE.DAT* → *Descargar* (o se deja en la carpeta configurada). En A3:
Utilidades → Importar/Exportar → Enlace contable → Enlazar.

Una factura exportada no se vuelve a exportar ni se puede pasar a borrador.
*Revertir exportación* libera las facturas (solo si el fichero no se importó).

Limitaciones conocidas
======================

* El número de factura de A3 tiene 10 caracteres: los números más largos se
  acortan como prefijo + año + secuencia (``INV/2026/00001`` → ``INV2600001``).
* No genera registros de alta de subcuentas (tipo C): A3 crea la subcuenta con
  el nombre y NIF de la cabecera de factura.
* No incluye cobros/pagos ni bienes de inversión (tipo de factura 3).
* Validar siempre la primera importación en una empresa de pruebas de A3.
