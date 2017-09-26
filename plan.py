# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.modules.product import TemplateFunction
from trytond.pool import Pool, PoolMeta
from trytond.config import config

__all__ = ['PlanCostType', 'PlanCost', 'Plan']
__metaclass__ = PoolMeta

DIGITS = (16, config.getint('product', 'price_decimal', default=4))
_ZERO = Decimal('0.0')


class PlanCostType:
    __name__ = 'product.cost.plan.cost.type'
    minimum_percent = fields.Float('Minimum %', required=True)

    @staticmethod
    def default_minimum_percent():
        return 0.0


class PlanCost:
    'Plan Cost'
    __name__ = 'product.cost.plan.cost'

    minimum = fields.Function(fields.Float('Minimum %', digits=DIGITS),
        'on_change_with_minimum')
    margin_percent = fields.Float('Margin %', required=True, digits=(16, 4))
    margin = fields.Function(fields.Numeric('Margin', digits=DIGITS),
        'on_change_with_margin')

    @classmethod
    def __setup__(cls):
        super(PlanCost, cls).__setup__()
        cls._error_messages.update({
                'minimum_margin': ('Invalid margin for "%s". Margin "%s" must '
                    'be greather than minimum "%s".'),
                })

    @classmethod
    def validate(cls, costs):
        super(PlanCost, cls).validate(costs)
        for line in costs:
            line.check_minimum()

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if 'margin_percent' not in values:
                values['margin_percent'] = 0
        return super(PlanCost, cls).create(vlist)

    def check_minimum(self):
        if not self.margin_percent >= self.minimum:
            self.raise_user_error('minimum_margin', (self.rec_name,
                    self.margin_percent * 100.0, self.minimum * 100.0))

    @fields.depends('type')
    def on_change_with_minimum(self, name=None):
        return self.type.minimum_percent

    @fields.depends('cost', 'margin_percent')
    def on_change_with_margin(self, name=None):
        if not self.cost or not self.margin_percent:
            return _ZERO
        digits = self.__class__.margin.digits[1]
        return Decimal(self.cost * Decimal(self.margin_percent).quantize(
                Decimal(str(10 ** - digits))))


class Plan:
    __name__ = 'product.cost.plan'

    product_list_price = fields.Function(fields.Numeric('Product List Price',
            digits=DIGITS),
        'get_product_list_price')
    margin = fields.Function(fields.Numeric('Margin', digits=DIGITS),
        'get_margin')
    margin_percent = fields.Function(fields.Numeric('Margin %',
            digits=(16, 4)),
        'get_margin_percent')
    list_price = fields.Function(fields.Numeric('Unit List Price',
            digits=DIGITS),
        'get_list_price')

    @classmethod
    def __setup__(cls):
        super(Plan, cls).__setup__()
        cls._buttons.update({
                'update_product_list_price': {
                    'icon': 'tryton-refresh',
                    },
                })

    def get_product_list_price(self, name):
        return self.product.list_price if self.product else None

    def get_margin(self, name):
        digits = self.__class__.margin.digits[1]
        return Decimal(sum(c.on_change_with_margin() or Decimal('0.0')
                for c in self.costs)).quantize(Decimal(str(10 ** -digits)))

    def get_margin_percent(self, name):
        if self.cost_price == _ZERO or self.margin is None:
            return
        return (self.margin / self.cost_price).quantize(Decimal('0.0001'))

    def get_list_price(self, name):
        list_price = self.cost_price if self.cost_price else Decimal('0.0')
        if self.margin:
            list_price += self.margin
        return list_price

    @classmethod
    @ModelView.button
    def update_product_list_price(cls, plans):
        for plan in plans:
            if not plan.product:
                continue
            plan._update_product_list_price()
            plan.product.save()
            plan.product.template.save()

    def _update_product_list_price(self):
        pool = Pool()
        Uom = pool.get('product.uom')

        assert self.product
        list_price = Uom.compute_price(self.uom, self.list_price,
            self.product.default_uom)
        if (hasattr(self.product.__class__, 'list_price') and not
                isinstance(self.product.__class__.list_price, TemplateFunction)
                ):
            digits = self.product.__class__.list_price.digits[1]
            list_price = list_price.quantize(Decimal(str(10 ** -digits)))
            self.product.list_price = list_price
        else:
            digits = self.product.template.__class__.list_price.digits[1]
            list_price = list_price.quantize(Decimal(str(10 ** -digits)))
            self.product.template.list_price = list_price

    def _get_cost_line(self, cost_type):
        vals = super(Plan, self)._get_cost_line(cost_type)
        if cost_type.minimum_percent:
            vals['margin_percent'] = cost_type.minimum_percent
        return vals
