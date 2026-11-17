{
    "name": "Seguimiento de pedidos a fábrica",
    "summary": "Situación de los pedidos de compra a fabricantes (solicitado, en producción, "
    "en tránsito, recibido parcial, recibido), datos de cada envío (tracking, transporte, "
    "llegada prevista) y documentos de inspección por producto",
    "version": "20.0.1.0.0",
    "category": "Inventory/Purchase",
    "author": "Solfix FM",
    "license": "LGPL-3",
    "depends": ["purchase_stock"],
    "data": [
        "views/purchase_order_views.xml",
        "views/stock_picking_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
