# -*- coding: utf-8 -*-
{
    "name": "ProSite",
    "summary": """Module that adds custom website building blocks according to the company theme.""",
    "description": """
        This module controls the custom theme of the website and adds several customizable blocks for the empty page template, like the footer, header, and main content. It also adds a variety of drag-and-drop blocks with many options available to alter the appearance, functionality, etc. of forms and info sections.
    """,
    "author": "Ezekiel J. deBlois",
    "license": "LGPL-3",
    "depends": [
        "website",
    ],
    "data": [
        "views/header.xml",  # Include your header view
    ],
    "assets": {
        "web.assets_frontend": [
            "prosite/static/src/css/header.css",
            "prosite/static/src/js/header.js",
        ],
    },
    "version": "1.0",
    "installable": True,
    "application": False,
    "auto_install": False,
}
