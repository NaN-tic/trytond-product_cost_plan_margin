import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.modules.company.tests.tools import create_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate product_cost_plan_margin Module
        activate_modules('product_cost_plan_margin')

        # Create company
        _ = create_company()

        # Configuration production location
        Location = Model.get('stock.location')
        warehouse, = Location.find([('code', '=', 'WH')])
        production_location, = Location.find([('code', '=', 'PROD')])
        warehouse.production_location = production_location
        warehouse.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        product = Product()
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.producible = True
        template.type = 'goods'
        template.list_price = Decimal(30)
        template.save()
        product.template = template
        product.cost_price = Decimal(20)
        product.save()

        # Create Components
        meter, = ProductUom.find([('name', '=', 'Meter')])
        centimeter, = ProductUom.find([('symbol', '=', 'cm')])
        componentA = Product()
        templateA = ProductTemplate()
        templateA.name = 'component A'
        templateA.default_uom = meter
        templateA.type = 'goods'
        templateA.list_price = Decimal(2)
        templateA.save()
        componentA, = templateA.products
        componentA.cost_price = Decimal(1)
        componentA.save()
        componentB = Product()
        templateB = ProductTemplate()
        templateB.name = 'component B'
        templateB.default_uom = meter
        templateB.type = 'goods'
        templateB.list_price = Decimal(2)
        templateB.save()
        componentB, = templateB.products
        componentB.cost_price = Decimal(1)
        componentB.save()
        component1 = Product()
        template1 = ProductTemplate()
        template1.name = 'component 1'
        template1.default_uom = unit
        template1.producible = True
        template1.type = 'goods'
        template1.list_price = Decimal(5)
        template1.save()
        component1, = template1.products
        component1.cost_price = Decimal(2)
        component1.save()
        component2 = Product()
        template2 = ProductTemplate()
        template2.name = 'component 2'
        template2.default_uom = meter
        template2.type = 'goods'
        template2.list_price = Decimal(7)
        template2.save()
        component2, = template2.products
        component2.cost_price = Decimal(5)
        component2.save()

        # Create Bill of Material
        BOM = Model.get('production.bom')
        BOMInput = Model.get('production.bom.input')
        BOMOutput = Model.get('production.bom.output')
        component_bom = BOM(name='component1')
        input1 = BOMInput()
        component_bom.inputs.append(input1)
        input1.product = componentA
        input1.quantity = 1
        input2 = BOMInput()
        component_bom.inputs.append(input2)
        input2.product = componentB
        input2.quantity = 1
        output = BOMOutput()
        component_bom.outputs.append(output)
        output.product = component1
        output.quantity = 1
        component_bom.save()
        ProductBom = Model.get('product.product-production.bom')
        component1.boms.append(ProductBom(bom=component_bom))
        component1.save()
        bom = BOM(name='product')
        input1 = BOMInput()
        bom.inputs.append(input1)
        input1.product = component1
        input1.quantity = 5
        input2 = BOMInput()
        bom.inputs.append(input2)
        input2.product = component2
        input2.quantity = 150
        input2.unit = centimeter
        output = BOMOutput()
        bom.outputs.append(output)
        output.product = product
        output.quantity = 1
        bom.save()
        ProductBom = Model.get('product.product-production.bom')
        product.boms.append(ProductBom(bom=bom))
        product.save()

        # Create a cost plan for product (without child boms)
        CostPlan = Model.get('product.cost.plan')
        plan = CostPlan()
        plan.product = product
        plan.quantity = 1
        plan.save()
        plan.click('compute')
        plan.reload()
        c1, = plan.products.find([
            ('product', '=', component1.id),
        ], limit=1)
        self.assertEqual(c1.quantity, 5.0)
        c2, = plan.products.find([
            ('product', '=', component2.id),
        ], limit=1)
        self.assertEqual(c2.quantity, 150.0)
        self.assertEqual(plan.cost_price, Decimal('17.5'))
        raw_materials, = plan.costs
        self.assertEqual(raw_materials.minimum, 0.0)
        self.assertEqual(raw_materials.cost, Decimal('17.5'))
        self.assertEqual(raw_materials.margin, Decimal('0.0'))
        raw_materials.margin_percent = .2
        self.assertEqual(raw_materials.margin, Decimal('3.5'))
        raw_materials.save()
        plan.reload()
        self.assertEqual(plan.margin_percent, Decimal('0.2'))
        self.assertEqual(plan.margin, Decimal('3.5'))

        # Calc margin from list_price
        calc_margin_from_list_price = Wizard(
            'product.cost.plan.calc_margins_from_list_price', [plan])
        calc_margin_from_list_price.form.list_price = plan.list_price
        calc_margin_from_list_price.execute('calc')
        plan.reload()
        self.assertEqual(plan.list_price,
                         calc_margin_from_list_price.form.list_price)
