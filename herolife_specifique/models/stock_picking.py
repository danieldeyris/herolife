# -*- coding: utf-8 -*-

from odoo import models


class Picking(models.Model):
    _inherit = "stock.picking"

    def _get_delivered_lines_grouped(self):
        domain = [('picking_id', '=', self.id), ('qty_done', '!=', 0)]
        lines = self.env['stock.move.line'].read_group(domain, ['product_id', 'qty_done'], ['product_id'])
        result = [(
            self.env['product.product'].browse(data['product_id'][0]).default_code,
            self.env['product.product'].browse(data['product_id'][0]).name,
            data['qty_done'],
            self._get_delivered_lines_grouped_lot(data['product_id'][0])
        ) for data in lines]
        return result

    def _get_delivered_lines_grouped_lot(self, product):
        lots_report = False
        lots_ids = self.env['stock.move.line'].search([('picking_id', '=', self.id), ('qty_done', '!=', 0), ('product_id', '=', product)])
        lot_values = []
        for ml in lots_ids:
            if ml.lot_id:
                lot_values.append(
                    ml.lot_id.name
                )
        if len(lot_values):
            lots_report = ', '.join(lot_values)
        return lots_report

