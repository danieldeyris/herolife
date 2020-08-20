# -*- coding: utf-8 -*-
import re
import os
import io
import logging
import xlrd
import csv
import base64
import collections

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.mimetypes import guess_mimetype

FILE_TYPE_DICT = {
    'text/csv': ('csv', True, None),
    'application/vnd.ms-excel': ('xls', xlrd, 'xlrd'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('xlsx', True, 'xlrd >= 1.0.0'),
}
EXTENSIONS = {
    '.' + ext: handler
    for mime, (ext, handler, req) in FILE_TYPE_DICT.items()
}

_logger = logging.getLogger(__name__)


class MrpSerialProductMassProduce(models.TransientModel):
    _name = "mrp.serial.product.mass.produce"
    
    production_id = fields.Many2one('mrp.production', 'Production')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float(string='Quantity')
    next_qty = fields.Integer(string='Next Qty')
    to_serial_number = fields.Integer(string='To Serial Number')
    scan_lot = fields.Char('Scan Lot')
    lots_to_generate = fields.One2many('mrp.serial.product.mass.produce.line', 'parent_id', copy=True)
    file_import = fields.Binary('File to Import')
    file_import_name = fields.Char('File Name')
    company_id = fields.Many2one('res.company', 'Company', required=True, stored=True, index=True)
    def reload_wizard(self):
        wizard_id = self.copy()
        return {
            'name': _("Mass Produce Products"),
            'view_mode': 'form',
            'view_id': self.env.ref('hv_manufacturing_mass_sn.view_mrp_serial_product_mass_produce_wizard').id,
            'view_type': 'form',
            'res_model': 'mrp.serial.product.mass.produce',
            'res_id': wizard_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }

    @api.onchange('scan_lot')
    def _onchange_lot_name(self):
        if self.scan_lot:
            if self.product_qty == len(self.lots_to_generate):
                raise ValidationError('Cannot scan new serial number. Exceed the production limit.')
            search_lot = self.env['stock.production.lot'].search([('name', '=', self.scan_lot), ('product_id', '=', self.product_id.id)])
            duplicate_lot_on_generate = self.lots_to_generate.filtered(lambda o: o.lot_name == self.scan_lot)
            if duplicate_lot_on_generate:
                raise ValidationError('Already scanned.')

            is_not_unique = False
            if search_lot:
                is_not_unique = True
            values = [(0, 0, {'lot_name': self.scan_lot, 'parent_id': self._origin.id, 'product_id': self.product_id.id, 'is_not_unique': is_not_unique})]
            for line in self.lots_to_generate:
                values.append((0, 0, {'lot_name': line.lot_name, 'parent_id': line.parent_id.id, 'product_id': line.product_id.id, 'is_not_unique': line.is_not_unique}))
            self.update({'lots_to_generate': values})
            return

    def increase_numeric_string(self, numeric_string, value=1, get_number=False):
        # Check if numeric_string have prefix
        # try to split prefix and number
        split_numeric_string = re.split('(\d+)', numeric_string) 
        if split_numeric_string and split_numeric_string[0] == '':
            del split_numeric_string[0]
        if split_numeric_string and split_numeric_string[len(split_numeric_string)-1] == '':
            del split_numeric_string[len(split_numeric_string)-1]
        last_element = split_numeric_string and split_numeric_string[len(split_numeric_string)-1] or False

        if not last_element.isdigit():
            raise ValidationError('Serial number must end with digit(s).')

        # check if last element is a lot number string start with 00000xxx. E.g: 00000214
        # try to keep 00000 when parse int by splitting 00000 and xxx
        split_last_element = re.split('(^0+)', last_element) 
        if split_last_element[0] == '':
            del split_last_element[0]
        if split_last_element[len(split_last_element)-1] == '':
            del split_last_element[len(split_last_element)-1]

        if get_number:
            return int(split_last_element[len(split_last_element)-1])

        number_increasement = int(split_last_element[len(split_last_element)-1]) + value
        # Join last element back to string
        split_last_element[len(split_last_element)-1] = str(number_increasement)
        last_element = ''.join(split_last_element)
        # Join numeric_string back to string
        split_numeric_string[len(split_numeric_string)-1] = last_element
        numeric_string = ''.join(split_numeric_string)
        
        return numeric_string

    def check_before_generate(self):
        if not self.scan_lot:
            raise ValidationError('Please scan or fill in Scan Lot.')

        if self.product_id.tracking != 'serial':
            raise ValidationError('Exceed the production limit. You only need to generate one Lot for production.')

        if not self.next_qty and not self.to_serial_number:
            raise ValidationError('Please fill in either Next qty or To Serial Number.')

        if (self.production_id.product_qty - self.production_id.qty_produced) < (self.next_qty + len(self.lots_to_generate)):
            raise ValidationError('Exceed the production limit. Lots were generated : %s.\nAble to generate %s more' 
                                   % (len(self.lots_to_generate), (self.production_id.product_qty - self.production_id.qty_produced)-len(self.lots_to_generate)))
        
        current_lot_number = self.increase_numeric_string(self.scan_lot, get_number=True)
        if (self.production_id.product_qty - self.production_id.qty_produced) < ((self.to_serial_number - current_lot_number) + len(self.lots_to_generate)):
            raise ValidationError('Exceed the production limit. Lots were generated : %s.\nAble to generate %s more' 
                                   % (len(self.lots_to_generate), (self.production_id.product_qty - self.production_id.qty_produced)-len(self.lots_to_generate)))

    def action_generate_lots(self):
        self.check_before_generate()
        line_obj = self.env['mrp.serial.product.mass.produce.line']
        lot_number = self.scan_lot
        if self.next_qty:
            for i in range(self.next_qty):
                lot_number = self.increase_numeric_string(lot_number)
                duplicate_lot_on_generate = self.lots_to_generate.filtered(lambda o: o.lot_name == lot_number)
                if duplicate_lot_on_generate:
                    raise ValidationError('Lot : %s already existed in Lot List!' % (lot_number))
                line_id = self.lots_to_generate.create({'lot_name': lot_number, 'parent_id': self.id, 'product_id': self.product_id.id})
                line_id._onchange_lot_name()

        if self.to_serial_number and not self.next_qty:
            current_lot_number = self.increase_numeric_string(lot_number, get_number=True)
            if current_lot_number > self.to_serial_number:
                raise ValidationError('To Serial Number must greater than Scan Lot Number.')

            for i in range(self.to_serial_number - current_lot_number):
                lot_number = self.increase_numeric_string(lot_number)
                duplicate_lot_on_generate = self.lots_to_generate.filtered(lambda o: o.lot_name == lot_number)
                if duplicate_lot_on_generate:
                    raise ValidationError('Lot : %s already existed in Lot List!' % (lot_number))
                line_id = self.lots_to_generate.create({'lot_name': lot_number, 'parent_id': self.id, 'product_id': self.product_id.id})
                line_id._onchange_lot_name()

        return self.reload_wizard()

    def do_mass_produce(self):
        if any(o.is_not_unique for o in self.lots_to_generate):
            raise ValidationError('Lot name must be unique!')

        mrp_product_produce = self.env['mrp.product.produce'].create({})
        lot_object = self.env['stock.production.lot']
        for line in self.lots_to_generate:
            lot_vals = {
                'name': line.lot_name,
                'product_id': line.product_id.id,
                'product_qty': 1.0,
                'company_id': self.company_id.id,
            }
            lot_id = lot_object.create(lot_vals)
            mrp_product_produce.finished_lot_id = lot_id.id
            mrp_product_produce._onchange_qty_producing()
            mrp_product_produce.do_produce()

    def action_import_lots(self):
        self.ensure_one()
        if not self.file_import:
            raise ValidationError('Please upload a file.')

        self._read_file({})

        return self.reload_wizard()

    def _read_file(self, options):
        self.ensure_one()
        if self.file_import_name:
            p, ext = os.path.splitext(self.file_import_name)
            if ext in EXTENSIONS:
                return getattr(self, '_read_' + ext[1:])(options)

        else:
            ValidationError('Please re-upload the file.')

        raise ValidationError("Unsupported file format \"{}\", import only supports CSV, XLS and XLSX".format(ext[1:]))

    def _read_xls(self, options):
        book = xlrd.open_workbook(file_contents=base64.b64decode(self.file_import))
        sheet = book.sheet_by_index(0)
        if self.product_id.tracking != 'serial' and sheet.nrows > 1:
            raise ValidationError('Exceed the production limit. You only need to generate one Lot for production.')

        if sheet.nrows > (self.production_id.product_qty - self.production_id.qty_produced)-len(self.lots_to_generate):
            raise ValidationError('Exceed the production limit. Lots were generated : %s.\nAble to generate %s more' 
                                   % (len(self.lots_to_generate), (self.production_id.product_qty - self.production_id.qty_produced)-len(self.lots_to_generate)))
        for row in range(0, sheet.nrows):
            cell_type = sheet.cell_type(row, 0)
            if cell_type == xlrd.XL_CELL_EMPTY:
                raise ValidationError('Empty cell at row : %s' % (row+1))
            lot_number = sheet.cell(row, 0).value
            duplicate_lot_on_generate = self.lots_to_generate.filtered(lambda o: o.lot_name == lot_number)
            if duplicate_lot_on_generate:
                raise ValidationError('Line : %s - Lot : %s already existed in Lot List.' % (row+1, lot_number))
            line_id = self.lots_to_generate.create({'lot_name': lot_number, 'parent_id': self.id, 'product_id': self.product_id.id})
            line_id._onchange_lot_name()
        self.file_import = False
            
    _read_xlsx = _read_xls

    def _read_csv(self, options):
        bytes_data = base64.decodebytes(self.file_import)
        string_data = io.StringIO(bytes_data.decode())
        reader = csv.reader(string_data)
        rows = list(reader)
        if self.product_id.tracking != 'serial' and len(rows) > 1:
            raise ValidationError('Exceed the production limit. You only need to generate one Lot for production.')

        if len(rows) > (self.production_id.product_qty - self.production_id.qty_produced)-len(self.lots_to_generate):
            raise ValidationError('Exceed the production limit. Rows in file : %s.\nAble to generate %s more'
                                   % (len(rows), (self.production_id.product_qty - self.production_id.qty_produced)-len(self.lots_to_generate)))
        for index,row in enumerate(rows):
            if not row:
                raise ValidationError('Empty cell at row : %s' % (index+1))
            lot_number = row[0]
            duplicate_lot_on_generate = self.lots_to_generate.filtered(lambda o: o.lot_name == lot_number)
            if duplicate_lot_on_generate:
                raise ValidationError('Line : %s - Lot : %s already existed in Lot List.' % (index+1, lot_number))
            line_id = self.lots_to_generate.create({'lot_name': lot_number, 'parent_id': self.id, 'product_id': self.product_id.id})
            line_id._onchange_lot_name() 
        self.file_import = False
     
class MrpSerialProductMassProduceLine(models.TransientModel):
    _name = "mrp.serial.product.mass.produce.line"

    parent_id = fields.Many2one('mrp.serial.product.mass.produce', 'Production')
    product_id = fields.Many2one('product.product', 'Product')
    lot_name = fields.Char('Lot')
    is_not_unique = fields.Boolean('Is Duplicate')
    
    @api.onchange('lot_name')
    def _onchange_lot_name(self):
        search_lot = self.env['stock.production.lot'].search([('name', '=', self.lot_name), ('product_id', '=', self.product_id.id)])
        if search_lot:
            self.is_not_unique = True
        else:
            self.is_not_unique = False