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

from openerp.tests.common import TransactionCase

class ProductVariantCase(TransactionCase):

    def setUp(self):
        super(ProductVariantCase, self).setUp()
        self.cost_methods = ['standard', 'average', 'real']
        self.template = self.env.ref(
            'product.product_product_4_product_template')
        self.products = self.template.product_variant_ids
        partner_obj = self.env['res.partner']

        partners = partner_obj.search([('supplier', '=', True)])
        if len(partners) < 3:
            for partner in ['supplier_1', 'supplier_2', 'supplier_3']:
                partner_obj.create({'supplier': 1, 'name': partner})
            partners = partner_obj.search([('supplier', '=', True)])
        self.partners = partners

    def test01a_set_cost_price_direct_write(self):
        for cost_method in self.cost_methods:
            self.products[0].product_tmpl_id.cost_method = cost_method
            with self.subTest(cost_method=cost_method):
                for extra, product in enumerate(self.products, 1):
                    product.standard_price = product.standard_price + extra
                new_costs = self.products.mapped('standard_price')
                # Just in case behaviour of mapped changes to remove duplicates
                # which will render next assertion pointless
                self.assertTrue(len(new_costs), len(self.products))
                # Ensure that each cost is different
                self.assertTrue(len(new_costs), len(set(new_costs)))

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
        def test01b_standard():
            pass

        def test01b_average():
            pass

        def test01b_real():
            pass

        #make sure that non realtime fails

        #test changing at template_level

        #test changing at product level
        for cost_method in self.cost_methods:
            self.products[0].product_tmpl_id.cost_method = cost_method
            with self.subTest(cost_method=cost_method):
                func = eval('test01b_%s' % cost_method)

    def test02a_get_cost_price_directly(self):
        pass

    def test03a_get_cost_price_from_pricelist(self):
        pass

    def test05_set_product_price_history(self):
        pass

    def test05_create_supplierinfo(self):
        def check_assertions():
            # Each product has correct number of records
            self.assertEqual(len(tmpl.seller_ids), 3)
            self.assertEqual(len(product_1.seller_ids), 2)
            self.assertEqual(len(product_2.seller_ids), 2)

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

    def test07_get_supplierinfo(self):
        pass


