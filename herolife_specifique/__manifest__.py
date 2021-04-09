# -*- coding: utf-8 -*-
{
    'name': "Phidias : specifique Herolife",

    'summary': """
        Phidias : specifique Herolife
        """,

    'description': """
        Phidias : specifique Herolife
    """,

    'author': "Phidias",
    'website': "http://www.phidias.fr",
    'category': 'Uncategorized',
    'version': '13.0.0.6',

    # any module necessary for this one to work correctly
    'depends': [
        'sale',
        'stock',
        'purchase',
        'web',
    ],
    "data": [
        'reports/custom_report_order_document.xml',
        'views/assets.xml',
        'reports/custom_report_headerfooter_boxed.xml',
        'reports/custom_report_invoice_document.xml',
        'reports/custom_report_invoice_document_with_payment.xml',
        'reports/custom_report_delivery.xml',
    ],
}
