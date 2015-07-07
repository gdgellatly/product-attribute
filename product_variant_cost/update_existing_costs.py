# -*- coding: utf-8 -*-

def update_existing_costs(cr, registry):
    """
    In order for this module to function correctly, once installed
    we must set all existing products cost price to be equal to the
    current cost of the parent template.
    :param cr: database cursor
    :return:
    """
    # Not strictly necessary as there shouldn't be existing entries,
    # but may have tried other modules that didn't clean up after
    # themselves or if a v7 migration may have used a different solution
    # related to product_variant_multi
    cr.execute("""
DELETE FROM ir_property
WHERE name='standard_price' AND res_id LIKE 'product.product%';""")

    cr.execute("""
INSERT INTO ir_property (name, type, company_id, fields_id, res_id, value_float)
SELECT 'standard_price', 'float', irp.company_id, f.id,
'product.product,' || p.id, irp.value_float
FROM ir_property irp
LEFT JOIN product_product p ON (
p.product_tmpl_id=CAST(SPLIT_PART(irp.res_id, ',', 2) as INTEGER)),
ir_model_fields f
WHERE (f.name = 'standard_price' AND f.model='product.product')
AND (irp.name='standard_price' AND irp.res_id like 'product.template%');""")
