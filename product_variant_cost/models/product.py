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

from openerp import api, fields, models
from openerp.addons.decimal_precision import decimal_precision as dp


class ProductPriceHistory(models.Model):
    _inherit = 'product.price.history'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_seller_ids(self):
        for product in self:
            product.computed_seller_ids = product.seller_ids.filtered(
                lambda r: not r.variant_id or r.variant_id == product)

    def _search_seller_ids(self):
        return [('product_tmpl_id', 'in',
                 set(p.product_tmpl_id.id for p in self)),
                '|', ('variant_id', '=', False),
                ('variant_id', 'in', self.ids)]

    def _write_seller_ids(self):
        for product in self:
            for supplier in self.computed_seller_ids:
                if not supplier.product_tmpl_id:
                    supplier.product_tmpl_id = product.product_tmpl_id
                    supplier.variant_id = product.id
                    supplier.create()
                else:
                    supplier.write()

        return True

    # Due to the way product inherits from product template
    # all existing code (at least in official addons) accesses
    # via product.standard_price will receive this rather than
    # the template variable of the same name
    standard_price = fields.Float(
        digits_compute=dp.get_precision('Product Price'),
        help="Cost price of the product used for standard stock valuation in "
             "accounting and used as a base price on purchase orders. "
             "Expressed in the default unit of measure of the product.",
        groups="base.group_user",
        string="Cost Price",
        company_dependent=True)

    # computed_seller_ids = fields.One2many(
    #     comodel_name='product.supplierinfo',
    #     inverse_name='variant_id',
    #     string='Suppliers',
    #     compute='_compute_seller_ids',
    #     search='_search_seller_ids',
    #     inverse='_write_seller_ids'
    # )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

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



