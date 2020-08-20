# -*- coding: utf-8 -*-
{
    'name': 'Manufacturing - Mass Serial Number',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Manufacturing - Mass Serial Number',
    'website': 'http://havi.com.au',
    'depends': [
        'mrp',
    ],
    'author': 'Havi Technology',
    'price': 99,
    'currency': "EUR",
    'data': [
        'views/mrp_production.xml',
        'wizard/mrp_serial_product_mass_produce.xml',
    ],
    'application': True,
    'installable': True,
}
