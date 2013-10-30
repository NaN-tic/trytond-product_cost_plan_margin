from trytond.model import fields, ModelSQL, ModelView, Workflow
from trytond.pool import PoolMeta

__all__ = ['PlanMarginType', 'PlanMargin', 'Plan']


class PlanMarginType(ModelSQL, ModelView):
    'Plan Margin Type'
    __name__ = 'product.cost.plan.margin.type'
    name = fields.Char('Name', required=True)
    minimum = fields.Float('Minimum %', required=True)


class PlanMargin(ModelSQL, ModelView):
    'Plan Margin'
    __name__ = 'product.cost.plan.margin'
    plan = fields.Many2One('product.cost.plan', 'Plan', required=True)
    type = fields.Many2One('product.cost.plan.margin.type', 'Type',
        required=True)
    cost = fields.Numeric('Cost', required=True)
    minimum = fields.Function(fields.Float('Minimum'), 'get_minimum')
    margin_percent = fields.Float('Margin %', required=True)
    margin = fields.Function(fields.Numeric('Margin'), 'get_margin')

    def get_minimum(self):
        return self.type.minimum

    def get_margin(self):
        return self.cost * self.margin_percent


class Plan:
    __metaclass__ = PoolMeta
    __name__ = 'product.cost.plan'
    margins = fields.One2Many('product.cost.plan.margin', 'plan', 'Margins')
    unit_margin = fields.Function(fields.Float('Unit Margin'), 'get_margins')
    percent_margin = fields.Function(fields.Float('Margin %'), 'get_margins')

    @classmethod
    def get_margins(cls, plans, names):
        res = {}.fromkeys(names, {})
        for plan in plans:
            # TODO:
            res['unit_margin'][plan.id] = 0.0
            res['percent_margin'][plan.id] = 0.0
        return res

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(cls, productions):
         '''
         Create margin lines
         '''
         pass
