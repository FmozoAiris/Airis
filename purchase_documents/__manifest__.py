{
    "name": "Solfix - Envíos e inspección en compras a fábrica",
    "summary": "Amplía el seguimiento de pedidos a fábrica (custom_purchase): datos de cada envío "
    "(medio, transitario, tracking, salida, llegada prevista), situación 'Parcial, resto en "
    "tránsito' y documentos de inspección por producto",
    "version": "20.0.2.0.0",
    "category": "Inventory/Purchase",
    "author": "Solfix FM",
    "license": "LGPL-3",
    "depends": ["custom_purchase"],
    "data": [
        "views/purchase_order_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
