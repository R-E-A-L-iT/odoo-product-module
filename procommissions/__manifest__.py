{
    'name': 'Commissions',
    'version': '1.0',
    'summary': 'Module to manage commission reports',
    'category': 'Hidden',
    'author': 'Ezekiel J. deBlois',
    'depends': ['base', 'crm', 'sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/data.xml',
        'views/menu_views.xml',
        'views/commissions_views.xml',
        'views/sale_order_views.xml'
        # 'views/invoice_views.xml'
    ],
    'application': True,
    'installable': True,
}