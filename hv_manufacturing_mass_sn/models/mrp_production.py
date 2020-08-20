# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def open_mass_produce_product(self):
        self.ensure_one()
        vals = {
            'production_id': self.id,
            'product_id': self.product_id.id,
            'product_qty': self.product_qty - self.qty_produced,
            'company_id': self.company_id.id,
        }
        wiz_id = self.env['mrp.serial.product.mass.produce'].create(vals)
        return {
            'name': _('Mass Produce Products'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.serial.product.mass.produce',
            'view_id': self.env.ref('hv_manufacturing_mass_sn.view_mrp_serial_product_mass_produce_wizard').id,
            'target': 'new',
            'res_id': wiz_id.id,
            'flags': {'form': {'action_buttons': True},}
        }