#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.

from trytond.pool import Pool
from .plan import *

def register():
    Pool.register(
        CalcMarginsFromListPriceStart,
        PlanCostType,
        PlanCost,
        Plan,
        module='product_cost_plan_margin', type_='model')
    Pool.register(
        CalcMarginsFromListPrice,
        module='product_cost_plan_margin', type_='wizard')
