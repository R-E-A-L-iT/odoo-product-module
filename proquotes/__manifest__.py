# -*- coding: utf-8 -*-
{
    "name": "Proquotes",
    "summary": """
		Quote Upgrade Module that adds Advanced Features""",
    "description": """
		Module that allows advanced Quote features. Like Folding Sections, Improved Optional Products, and Multiple Choice Sections
	""",
    "author": "Ty Cyr",
    "license": "LGPL-3",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Sales",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "web",
        "mail",
        "mail_group",
        "account",
        "proportal",
        "stock",
        "website",
        "sale_management",
        "sale",
        "hr",
        "digest",
        "portal",
        "contacts",
        "stock_account",
        "sale_project",
        "website_sale",
        "sale_timesheet",
    ],
    # "product",
    "assets": {
        "web.assets_common": [
            "proquotes/static/src/CSS/foldProducts.css",
            "proquotes/static/src/CSS/pdf.css",
            "proquotes/static/src/CSS/user-info.css",
            "proquotes/static/src/CSS/login.css",
            "proquotes/static/src/CSS/quoteStyle.css",
            "proquotes/static/src/CSS/quoteHeaderText.css",
            "proquotes/static/src/CSS/rental_fold.css",
            "proquotes/static/src/CSS/backend.css",
            "proquotes/static/src/JS/fold.js",
            "proquotes/static/src/JS/poNumber.js",
            "proquotes/static/src/JS/rental.js",
            "proquotes/static/src/JS/website_preview.js",
        ],
        'web.assets_frontend': [
            "proquotes/static/src/JS/price.js",
            "proquotes/static/src/JS/fold.js",
            "proquotes/static/src/JS/poNumber.js",
            "proquotes/static/src/JS/rental.js",
            "proquotes/static/src/JS/website_preview.js",
        ],
        'web.assets_backend': [
            "proquotes/static/src/JS/website_preview.js",
        ],
    },

    "version": "17.0",

    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/Other/tax.xml",
        "views/Quote/quotesBackend.xml",
        "views/Quote/quotesFrontend.xml",
        "views/Quote/quotesPDF.xml",
        "views/Quote/rentalTerms.xml",
        "views/Quote/quotesTemplates.xml",
        "views/Quote/quoteLogo.xml",
        "views/Quote/renewalText.xml",
        "views/Quote/quoteRentalAddress.xml",
        "views/Quote/table-align.xml",
        "views/Quote/pricelistFilter.xml",
        "views/Quote/quoteMailWizard.xml",
        "views/Other/mail.xml",
        "views/Other/deliverPDF.xml",
        "views/Other/project_task.xml",
        "views/Other/pdf_boxed.xml",
        "views/Other/section_name.xml",
        "views/Other/internal_company_backend.xml",
        "views/Other/internal_user_backend.xml",
        "views/Other/renewal.xml",
        "views/Other/header_footer.xml",
        # "views/Other/product_backend.xml",
        "views/Invoice/invoicePDF.xml",
        "views/Invoice/invoice_lot.xml",
        "views/Invoice/invoiceBackend.xml",
        # "views/Invoice/invoicePayment.xml",
        "views/PO/PO_Frontend.xml",
        "views/PO/PO_Backend.xml",
        "views/PO/PO_PDF.xml",
        "views/Other/quoteEmailFooter.xml",
        "views/Other/helpdeskTicket.xml",
        "views/Other/header_footer_values.xml",
        # "views/Other/translated_terms.xml",
        # "views/Invoice/invoicePayment.xml",
        # "views/Other/product_backend.xml",
        #         'models/quoteNotify.py'
    ],
    # only loaded in demonstration mode
    # "demo": [
    #     "demo/demo.xml",
    # ],
}
