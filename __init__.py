#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.pool import Pool
from . import plan

def register():
    Pool.register(
        plan.CalcMarginsFromListPriceStart,
        plan.PlanCostType,
        plan.PlanCost,
        plan.Plan,
        module='product_cost_plan_margin', type_='model')
    Pool.register(
        plan.CalcMarginsFromListPrice,
        module='product_cost_plan_margin', type_='wizard')
