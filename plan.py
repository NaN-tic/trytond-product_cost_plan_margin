from decimal import Decimal

from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool, PoolMeta

__all__ = ['PlanMarginType', 'PlanMargin', 'Plan']
__metaclass__ = PoolMeta

_ZERO = Decimal('0.0')
MODULE_NAME = 'product_cost_plan_margin'


class PlanMarginType(ModelSQL, ModelView):
    'Plan Margin Type'
    __name__ = 'product.cost.plan.margin.type'

    name = fields.Char('Name', required=True, translate=True)
    minimum_percent = fields.Float('Minimum %', required=True)

    @staticmethod
    def default_minimum_percent():
        return 0.0


class PlanMargin(ModelSQL, ModelView):
    'Plan Margin'
    __name__ = 'product.cost.plan.margin'

    plan = fields.Many2One('product.cost.plan', 'Plan', required=True)
    type = fields.Many2One('product.cost.plan.margin.type', 'Type',
        required=True)
    cost = fields.Numeric('Cost', required=True)
    minimum = fields.Function(fields.Float('Minimum %', digits=(14, 4),
            on_change_with=['type']),
        'on_change_with_minimum')
    margin_percent = fields.Float('Margin %', required=True, digits=(14, 4))
    margin = fields.Function(fields.Numeric('Margin',
            on_change_with=['cost', 'margin_percent']),
        'on_change_with_margin')

    @classmethod
    def __setup__(cls):
        super(PlanMargin, cls).__setup__()
        cls._error_messages.update({
                'minimum_margin': ('Invalid margin for "%s". Margin "%s" must '
                    'be greather than minimum "%s".'),
                })

    def get_rec_name(self, name):
        return self.type.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('type.name',) + tuple(clause[1:])]

    @classmethod
    def validate(cls, margins):
        super(PlanMargin, cls).validate(margins)
        for margin in margins:
            margin.check_minimum()

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


class Plan:
    __name__ = 'product.cost.plan'

    margins = fields.One2Many('product.cost.plan.margin', 'plan', 'Margins')
    unit_margin = fields.Function(fields.Float('Unit Margin', digits=(14, 4)),
        'get_margins')
    percent_margin = fields.Function(fields.Float('Margin %', digits=(14, 4)),
        'get_margins')
    unit_price = fields.Function(fields.Numeric('Unit Price',
            on_change_with=['quantity', 'total_cost', 'unit_margin']),
        'on_change_with_unit_price')

    @classmethod
    def __setup__(cls):
        for fname in ('state', 'margins', 'product_cost', 'operation_cost'):
            if not fname in cls._fields.keys():
                continue
            if not fname in cls.total_cost.on_change_with:
                cls.total_cost.on_change_with.append(fname)
                cls.total_cost.depends.append(fname)
        super(Plan, cls).__setup__()

    def on_change_with_total_cost(self, name=None):
        cost = Decimal('0.0')
        for margin in self.margins:
            cost += Decimal(str(margin.cost))
        return cost

    def on_change_with_unit_price(self, name=None):
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
            total_margin = sum(Decimal(str(m.margin)) for m in plan.margins)

            if plan.total_cost != _ZERO and 'percent_margin' in names:
                res['percent_margin'][plan.id] = round(float(total_margin /
                    plan.total_cost), 4)

            quantity = Decimal(str(plan.quantity))
            if quantity != _ZERO and 'unit_margin' in names:
                res['unit_margin'][plan.id] = round(float(total_margin /
                        quantity), 4)
        return res

    @classmethod
    def reset(cls, plans):
        pool = Pool()
        MarginLines = pool.get('product.cost.plan.margin')

        super(Plan, cls).reset(plans)

        to_delete = []
        for plan in plans:
            types = [x[0]for x in plan.get_margin_types()]
            for margin in plan.margins:
                if margin.type in types:
                    to_delete.append(margin)

        if to_delete:
            MarginLines.delete(to_delete)

    @classmethod
    def compute(cls, plans):
        pool = Pool()
        MarginLines = pool.get('product.cost.plan.margin')

        super(Plan, cls).compute(plans)
        to_create = []

        for plan in plans:
            to_create.extend(plan.get_margin_lines())
        if to_create:
            MarginLines.create(to_create)

    def get_margin_lines(self):
        " Returns the margin lines to be created on compute "
        ret = []

        for margin_type, field_name in self.get_margin_types():
            cost = getattr(self, field_name, 0.0)
            ret.append({
                    'type': margin_type.id,
                    'margin_percent': margin_type.minimum_percent,
                    'cost': Decimal(str(cost)),
                    'plan': self.id,
                    })
        return ret

    def get_margin_types(self):
        """
        Returns a list of values with the margin types and the field to get
        their cost.
        """
        pool = Pool()
        MarginType = pool.get('product.cost.plan.margin.type')
        ModelData = pool.get('ir.model.data')
        ret = []
        for xml_id, field_name in [('raw_materials', 'product_cost'),
                ('operations', 'operation_cost')]:
            type_ = MarginType(ModelData.get_id(MODULE_NAME, xml_id))
            ret.append((type_, field_name,))
        return ret
