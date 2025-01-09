{
    'name': 'ProExpenses',
    'version': '1.0',
    'summary': 'Module to make the transfer and management of inter-company expenses more efficient',
    'category': 'Hidden',
    'author': 'Ezekiel J. deBlois',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/bank_statement_views.xml',
    ],
    'application': False,
    'installable': True,
}