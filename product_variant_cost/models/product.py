# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP / Odoo, Open Source Management Solution - module extension
#    Copyright (C) 2014- O4SB (<http://openforsmallbusiness.co.nz>).
#    Author Graeme Gellatly <g@o4sb.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from openerp import api, fields, models
from openerp.exceptions import ValidationError
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.decimal_precision import decimal_precision as dp


class ProductPriceHistory(models.Model):
    _inherit = 'product.price.history'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    @api.depends('product_tmpl_id.seller_ids')
    def _compute_seller_ids(self):
        for product in self:
            product.seller_ids = product.product_tmpl_id.seller_ids.filtered(
                lambda r: not r.variant_id or r.variant_id == product)
            product.seller_id = (product.seller_ids and
                                 product.seller_ids[0].name or
                                 self.env['res.partner'])

    def _search_seller_ids(self):
        return [('product_tmpl_id', 'in',
                 list(set(p.product_tmpl_id.id for p in self))),
                '|', ('variant_id', '=', False),
                ('variant_id', 'in', self.ids)]

    @api.multi
    def write(self, vals):
        if 'seller_ids' in vals:
            pt_vals = {'seller_ids': vals['seller_ids']}
            tmpls = self.mapped('product_tmpl_id')
            tmpls.write(pt_vals)
        if 'standard_price' in vals:
            self._set_standard_price(vals['standard_price'])
        return super(ProductProduct, self).write(vals)

    @api.multi
    def create(self, vals):
        if 'standard_price' in vals:
            self._set_standard_price(vals['standard_price'])
        return super(ProductProduct, self).create(vals)

    @api.one
    def _set_standard_price(self, value):
        """ Store the standard price change in order to be able to retrieve
        the cost of a product template for a given date"""
        price_history_obj = self.env['product.price.history']
        user_company = self.env.user.company_id.id
        company_id = self._context.get('force_company', user_company)
        price_history_obj.create({
            'product_template_id': self.product_tmpl_id.id,
            'product_id': self.id,
            'cost': value,
            'company_id': company_id})

    # Due to the way product inherits from product template
    # all existing code (at least in official addons) accesses
    # via product.<field> and will receive this rather than
    # the template variable of the same name
    standard_price = fields.Float(
        digits_compute=dp.get_precision('Product Price'),
        help="Cost price of the product used for standard stock valuation in "
             "accounting and used as a base price on purchase orders. "
             "Expressed in the default unit of measure of the product.",
        groups="base.group_user",
        string="Cost Price",
        company_dependent=True)

    seller_ids = fields.One2many(
        comodel_name='product.supplierinfo',
        inverse_name='variant_id',
        string='Suppliers',
        compute='_compute_seller_ids',
        search='_search_seller_ids',
    )

    seller_id = fields.Many2one(
        comodel_name='res.partner',
        string='Main Supplier',
        help="Main Supplier who has highest priority in Supplier List.",
        store=True,
        compute='_compute_seller_ids'
    )

    def _get_locations(self):
        user_company_id = self.env.user.company_id.id
        location_obj = self.env['stock.location']
        return location_obj.search([('usage', '=', 'internal'),
                                    ('company_id', '=', user_company_id)])

    @api.multi
    def get_history_price(self, company_id, date=None):
        self.ensure_one()
        if date is None:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        price_history_obj = self.env['product.price.history']
        history_ids = price_history_obj.search([
            ('company_id', '=', company_id),
            ('product_id', '=', self.ids[0]),
            ('datetime', '<=', date)], limit=1)
        if not history_ids:
            history_ids = price_history_obj.search([
                ('company_id', '=', company_id),
                ('product_id', '=', False),
                ('product_template_id', '=', self[0].product_tmpl_id.id),
                ('datetime', '<=', date)], limit=1)
        if history_ids:
            return history_ids[0]['cost']
        return 0.0

    @api.one
    def _get_price_change_accounts(self):
        """
        Mainly here as a hook for anglosaxon which should use P&L
        expense accounts rather than stock input and output
        """
        datas = self.get_product_accounts()
        datas.update({
            'valuation_account': datas['property_stock_valuation_account_id'],
            'debit_account': datas['stock_account_input'],
            'credit_account': datas['stock_account_output']})
        return datas

    @api.one
    def _prepare_price_change_move_vals(self, diff, qty):
        datas = self._get_price_change_accounts
        move_vals = {'journal_id': datas['stock_journal'],
                     'company_id': self.env.user.company_id.id}

        amount_diff = qty * diff
        if amount_diff > 0:
            debit_account_id = datas['debit_account']
            credit_account_id = datas['valuation_account']
        else:
            debit_account_id = datas['valuation_account']
            credit_account_id = datas['credit_account']
            amount_diff = -amount_diff

        lines = [(0, 0, {'name': _('Standard Price changed'),
                         'account_id': debit_account_id,
                         'debit': amount_diff,
                         'credit': 0.0,
                         'product_id': self.id,
                         }),
                 (0, 0, {'name': _('Standard Price changed'),
                         'account_id': credit_account_id,
                         'debit': 0,
                         'credit': amount_diff,
                         'product_id': self.id,
                         })]
        move_vals.update({'move_line': lines})
        return move_vals

    @api.multi
    def do_change_standard_price(self, new_price):
        """
        Changes the Standard Price of Product and
        creates an account move accordingly."""

        move_obj = self.env['account.move']
        locations = self._get_locations()
        for location in locations:
            records = self.with_context(
                {'location': location.id,
                 'compute_child': False}).browse(self.ids)
            for record in records:
                diff = record.standard_price - new_price
                if not diff:
                    continue

                qty = record.qty_available
                if qty:
                    # Accounting Entries
                    move_vals = record._prepare_change_price_move_vals(diff, qty)
                    move_obj.create(move_vals)
        self.write({'standard_price': new_price})
        return True


ALLOWED_COST_METHODS = ['average', 'standard']


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def do_change_standard_price(self, new_price):
        for record in self:
            if record.cost_method not in ALLOWED_COST_METHODS:
                raise ValidationError(
                    'Only records of type %s can be changed '
                    'using this method' % ','.join(ALLOWED_COST_METHODS))
            record.product_variant_ids.do_change_standard_price(new_price)
            record.write({'standard_price': new_price})
        return True

    def _set_standard_price(self, value):
        pass

    # price_get methods operate on products already


class ProductSupplierinfo(models.Model):
    """
    Inherit Product Supplier Info in order to allow
    information to be stored at the variant level.
    """
    _inherit = 'product.supplierinfo'

    # NOTE: we use the name variant_id to avoid confusion
    # with prior versions where product_id referred to a
    # template
    variant_id = fields.Many2one(
        comodel_name='product.product',
        string='Product')
