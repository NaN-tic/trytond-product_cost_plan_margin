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

    unit_margin = fields.Function(fields.Float('Unit Margin', digits=(14, 4)),
        'get_margins')
    percent_margin = fields.Function(fields.Float('Margin %', digits=(14, 4)),
        'get_margins')
    unit_price = fields.Function(fields.Numeric('Unit Price'),
        'get_unit_price')
    total_margin = fields.Function(fields.Numeric('Total Margin'),
        'get_margins')
    total_price = fields.Function(fields.Numeric('Total Price'),
        'get_total_price')

    def get_unit_price(self, name=None):
        if not self.total_cost or not self.quantity or not self.unit_margin:
            return Decimal('0.0')
        return ((self.total_cost / Decimal(str(self.quantity)))
            + Decimal(str(self.unit_margin)))

    @classmethod
    def get_margins(cls, plans, names):
        res = {}
        for name in names:
            res[name] = dict([(p.id, 0.0) for p in plans])

        for plan in plans:
            total_margin = sum(Decimal(str(m.margin)) for m in plan.costs)
            if 'total_margin' in names:
                res['total_margin'][plan.id] = total_margin

            if plan.total_cost != _ZERO and 'percent_margin' in names:
                res['percent_margin'][plan.id] = round(float(total_margin /
                    plan.total_cost), 4)

            quantity = Decimal(str(plan.quantity))
            if quantity != _ZERO and 'unit_margin' in names:
                res['unit_margin'][plan.id] = round(float(total_margin /
                        quantity), 4)
        return res

    def get_total_price(self, name):
        return self.total_cost + self.total_margin

    def get_cost_line(self, cost_type, field_name):
        res = super(Plan, self).get_cost_line(cost_type, field_name)
        res['margin_percent'] = cost_type.minimum_percent
        return res
