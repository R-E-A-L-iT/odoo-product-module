{

    # App information
    'name': 'Project Diagram Editor',
    'version': '16.0.0',
    'category': 'Services/Project',
    'summary': """ 
    	Allow to define Diagram/Flowchart in projct and task with Draw.IO in just single Click
        """,
    'description': """
    	Allow to define Diagram/Flowchart in projct and task with Draw.IO in just single Click
        """,

    # Dependencies
    'depends': ['project'],

    'data': [
        'views/project_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_diagram_codex/static/src/scss/project_diagram_codex.scss',
            'project_diagram_codex/static/src/js/project_diagram_codex_action.js',
            'project_diagram_codex/static/src/js/project_diagram_codex_component.js',
            'project_diagram_codex/static/src/js/project_diagram_codex_field.js',
            'project_diagram_codex/static/src/xml/project_diagram_codex.xml'
        ],
    },

    'license': 'LGPL-3',

    # Odoo Store Specific
    'images': [
        'static/description/cover.png',
    ],

    'price': 32,
    'currency': 'EUR',

    # Author
    'author': 'Codex Craft Solution',
    'website': 'codexcraftsolution@gmail.com',
    'maintainer': 'Codex Craft Solution',

    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,

}
