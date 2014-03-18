from decimal import Decimal

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['PlanCostType', 'PlanCost', 'Plan']
__metaclass__ = PoolMeta

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

    minimum = fields.Function(fields.Float('Minimum %', digits=(14, 4),
            on_change_with=['type']),
        'on_change_with_minimum')
    margin_percent = fields.Float('Margin %', required=True, digits=(14, 4))
    margin = fields.Function(fields.Numeric('Margin',
            on_change_with=['cost', 'margin_percent']),
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

    def on_change_with_minimum(self, name=None):
        return self.type.minimum_percent

    def on_change_with_margin(self, name=None):
        if not self.cost or not self.margin_percent:
            return _ZERO
        return Decimal(self.cost * Decimal(self.margin_percent).quantize(
                Decimal(str(10 ** - 2))))

    def update_cost_values(self, value):
        res = super(PlanCost, self).update_cost_values(value)
        self.cost = value
        res['margin'] = self.on_change_with_margin()
        return res


class Plan:
    __name__ = 'product.cost.plan'

    margin = fields.Function(fields.Numeric('Margin', digits=(16, 4),
            on_change_with=['costs']), 'on_change_with_margin')
    margin_percent = fields.Function(fields.Numeric('Margin %', digits=(14, 4),
            on_change_with=['costs', 'products', 'cost_price']),
        'on_change_with_margin_percent')
    unit_price = fields.Function(fields.Numeric('Unit Price', digits=(16, 4),
            on_change_with=['costs', 'products', 'cost_price']),
        'on_change_with_unit_price')

    def on_change_with_unit_price(self, name=None):
        unit_price = Decimal('0.0')
        if self.cost_price:
            unit_price += self.cost_price
        margin = self.on_change_with_margin()
        if margin:
            unit_price += margin
        return unit_price

    def on_change_with_margin(self, name=None):
        return sum(c.margin for c in self.costs)

    def on_change_with_margin_percent(self, name=None):
        if self.cost_price == _ZERO:
            return
        margin = self.on_change_with_margin()
        return margin / self.cost_price
