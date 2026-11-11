"""Bring over the developer-mode prototype fields, if present."""

COPIES = [
    ("x_fecha_proforma", "proforma_date"),
    ("x_fecha_produccion", "production_date"),
    ("x_fecha_envio", "departure_date"),
]


def post_init_hook(env):
    cr = env.cr
    moved = False
    for old, new in COPIES:
        cr.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name = 'purchase_order' AND column_name = %s",
            (old,),
        )
        if cr.rowcount:
            cr.execute(
                f'UPDATE purchase_order SET "{new}" = "{old}" WHERE "{old}" IS NOT NULL'  # noqa: S608
            )
            moved = True
    orders = env["purchase.order"].search([])
    if moved or orders:
        orders._compute_factory_status()
