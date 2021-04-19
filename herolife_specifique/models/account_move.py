# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models
from odoo.tools import float_is_zero

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoiced_order(self):
        orders_ids = self.mapped('invoice_line_ids.sale_line_ids.order_id')

        orders_values = False
        orders = []
        for ml in orders_ids:
            orders.append(ml.name)
        if len(orders):
            orders_values = ', '.join(orders)
        return orders_values


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    price_reduce = fields.Float(string="Price Reduce", compute="_compute_price_reduce", digits='Product Price')

    def _get_invoiced_lot_values_report(self):
        lots_report = False
        lots = self._get_invoiced_lot_values()
        if len(lots):
            lots_report = ', '.join(lots)
        return lots_report

    def _get_invoiced_lot_values(self):
        """ Get and prepare data to show a table of invoiced lot on the invoice's report. """
        self.ensure_one()

        if self.move_id.state == 'draft':
            return []

        move_ids = self.mapped('sale_line_ids.move_ids')
        stock_move_lines = move_ids.mapped('move_line_ids')

        # Prepare and return lot_values
        lot_values = []
        for ml in stock_move_lines:
            if ml.lot_id:
                lot_values.append(
                    ml.lot_id.name
                )
        return lot_values

    def _compute_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_unit * (1.0 - line.discount / 100.0)