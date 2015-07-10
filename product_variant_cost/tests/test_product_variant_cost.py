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

from random import randint
from openerp.tests.common import TransactionCase
from openerp.exceptions import ValidationError

partner_names = ['vc_supplier_1', 'vc_supplier_2', 'vc_supplier_3']

class ProductVariantCase(TransactionCase):

    def setUp(self):
        super(ProductVariantCase, self).setUp()
        self.cost_methods = ['standard', 'average', 'real']
        self.template = self.env.ref(
            'product.product_product_4_product_template')
        self.products = self.template.product_variant_ids

        self.unlink = False
        partner_obj = self.env['res.partner']
        partners = partner_obj.search([('supplier', '=', True)])
        if len(partners) < 3:
            for partner in partner_names:
                partner_obj.create({'supplier': 1, 'name': partner})
            partners = partner_obj.search([('supplier', '=', True)])
            self.unlink = True
        self.partners = partners

    # def tearDown(self):
    #     if self.unlink:
    #         partner_obj = self.env['res.partner']
    #         partners = partner_obj.search([('name', 'in', partner_names)])
    #         partners.unlink()

    def test01a_set_get_cost_price_directly(self):
        """
        Test the setting and getting of costs via a direct write then
        retrieval via both a direct read and pricelist read
        """
        pricelist = self.env.ref('purchase.list0')
        for cost_method in self.cost_methods:
            self.products[0].product_tmpl_id.cost_method = cost_method

            with self.subTest(cost_method=cost_method):
                comparison_costs = self.products.mapped('standard_price')
                for extra, product in enumerate(self.products, 1):
                    product.standard_price = product.standard_price + extra
                new_costs = self.products.mapped('standard_price')
                # Just in case behaviour of mapped changes to remove duplicates
                # which will render next assertion pointless
                self.assertTrue(len(new_costs), len(self.products))

                # Ensure that each cost is changed
                for idx, cost in enumerate(comparison_costs):
                    self.assertFalse(cost == new_costs[idx])
                    self.assertTrue(new_costs[idx] == cost + idx + 1)

                p_get_res = self.products.price_get(ptype='standard_price')
                new_costs = [p_get_res[p.id] for p in self.products]
                for idx, cost in enumerate(comparison_costs):
                    self.assertFalse(cost == new_costs[idx])
                    self.assertTrue(new_costs[idx] == cost + idx + 1)

                prod_qty_partner = [(x, 1.0, None) for x in self.products]
                res = pricelist.price_get_multi(prod_qty_partner)
                new_costs = [res[p.id][pricelist.id]for p in self.products]
                for idx, cost in enumerate(comparison_costs):
                    self.assertFalse(cost == new_costs[idx])
                    self.assertTrue(new_costs[idx] == cost + idx + 1)

    def test01b_set_cost_price_via_update_wizard(self):
        """
        Note: Update cost wizard is only functional for real_time valuation
        and cost methods of standard and average, however this is only
        secured by view.  It is available on both the template and variant
        form and uses context to determine action.

        The expected behaviour is for
        Templates: set all cost prices of products to the new price and
            perform accounting updates
        Products: change existing cost prices, not affecting others.
           For average cost it should average the template.

        For non supported operations an exception should be raised.
        :return:
        """
        def test01b_wiz_standard():
            wiz = cost_wizard.with_context(
                active_id=self.products[0].id,
                active_model='product.product').create({})
            wiz.new_price = new_price
            wiz.change_price()
            self.assertEqual(wiz.new_price, self.products[0].standard_price)

        def test01b_func_standard():
            self.products[0].do_change_standard_price(new_price)
            self.assertEqual(new_price, self.products[0].standard_price)

        def test01b_wiz_average():
            wiz = cost_wizard.with_context(
                active_id=self.products[0].id,
                active_model='product.product').create({})
            wiz.new_price = new_price
            wiz.change_price()
            self.assertEqual(wiz.new_price, self.products[0].standard_price)

        def test01b_func_average():
            self.products[0].do_change_standard_price(new_price)
            self.assertEqual(new_price, self.products[0].standard_price)

        def test01b_wiz_real():
            wiz = cost_wizard.with_context(
                active_id=self.products[0].id,
                active_model='product.product').create({})
            wiz.new_price = new_price
            self.assertRaises(
                ValidationError,
                wiz.change_price)

        def test01b_func_real():
            self.products[0].do_change_standard_price(new_price)
            self.assertRaises(
                ValidationError,
                self.products[0].do_change_standard_price, (new_price,))

        #make sure that non realtime fails

        #test changing at template_level

        #test changing at product level
        cost_wizard = self.env['stock.change.standard.price']
        for cost_method in self.cost_methods:
            self.products[0].product_tmpl_id.cost_method = cost_method
            with self.subTest(cost_method=cost_method):
                compare_cost = new_price = self.products[1].standard_price
                while new_price == compare_cost:
                    new_price = (randint(100, 500) / 100.0)
                eval('test01b_wiz_%s' % cost_method)
                # make sure comparison has not changed
                self.assertEqual(compare_cost, self.products[1].standard_price)

                new_price = (randint(501, 1000) / 100.0)
                while new_price == compare_cost:
                    new_price = (randint(501, 1000) / 100.0)
                eval('test01b_func_%s' % cost_method)
                self.assertEqual(compare_cost, self.products[1].standard_price)

    def test05_set_product_price_history(self):
        pass

    def test05_create_supplierinfo(self):
        def check_assertions():
            # Each product has correct number of records
            self.assertEqual(len(tmpl.seller_ids), 3)
            self.assertEqual(len(product_1.seller_ids), 2)
            self.assertEqual(len(product_2.seller_ids), 2)
            self.assertEqual(len(product_3.seller_ids), 1)

            # Each product has the correct main seller
            self.assertEqual(product_1.seller_id, partners[0])
            self.assertEqual(product_2.seller_id, partners[1])

            # ORM functions work on computed one2many
            self.assertNotIn(partners[2], product_3.seller_ids.mapped('name'))
            self.assertIn(partners[2], product_2.seller_ids.mapped('name'))

        partners = self.partners
        product_1 = self.products[0]
        product_2 = self.products[1]
        product_3 = self.products[2]
        tmpl = product_1.product_tmpl_id
        tmpl.seller_ids.unlink()

        # These vals should give us 3 lots of supplier info, 2 that are
        # Product specific, one with a higher, one with a lower sequence
        # than the default one
        vals = [(0, 0, {'variant_id': product_1.id,
                        'product_tmpl_id': tmpl.id,
                        'name': partners[0].id,
                        'sequence': 5}),
                (0, 0, {'product_tmpl_id': tmpl.id,
                        'variant_id': False,
                        'name': partners[1].id,
                        'sequence': 10}),
                (0, 0, {'product_tmpl_id': tmpl.id,
                        'variant_id': product_2.id,
                        'name': partners[2].id,
                        'sequence': 15})]

        #Test writing on product template
        tmpl.write({'seller_ids': vals})
        check_assertions()
        tmpl.seller_ids.unlink()

        #Test writing on product
        product_1.write({'seller_ids': vals[:-2]})
        product_2.write({'seller_ids': vals[-2:]})
        check_assertions()

    def test06_get_product_price_history(self):
        pass




