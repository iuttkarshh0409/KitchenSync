from decimal import Decimal,ROUND_HALF_UP
MOMO_PRICE_FLOOR=Decimal('69.00')
def money(v):return Decimal(str(v)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
def calculate_profitability(items:list[dict],config:dict,delivery_cost=0,other_cost=0):
 revenue=Decimal('0.00');ingredients=Decimal('0.00');warnings=[];violations=[];lines=[]
 for i in items:
  price=money(i['price']);qty=int(i['quantity']);discount=money(i.get('discount',0));effective=(price*qty-discount)/qty
  if i.get('brand')=='Momobuzz' and effective<MOMO_PRICE_FLOOR:violations.append(f"{i['name']} effective price {effective.quantize(Decimal('0.01'))} is below ₹69 per unit.")
  revenue+=price*qty-discount;cost=i.get('ingredient_cost_per_unit')
  if cost is None:warnings.append(f"Ingredient cost missing for {i['name']}.")
  else:ingredients+=money(cost)*qty
  lines.append({'menu_item_id':i['id'],'name':i['name'],'quantity':qty,'unit_price':str(price),'subtotal':str(money(price*qty-discount)),'ingredient_cost':None if cost is None else str(money(cost)*qty)})
 if config.get('platform_commission_percent') is None:warnings.append('Platform commission is not configured.')
 platform=money(revenue*money(config.get('platform_commission_percent',0))/Decimal(100));delivery=money(config.get('delivery_cost',0) if delivery_cost==0 else delivery_cost);other=money(other_cost)
 if config.get('delivery_cost') is None and delivery_cost==0:warnings.append('Delivery cost is not configured.')
 complete=not warnings;costs=ingredients+delivery+platform+other;profit=revenue-costs;margin=profit/revenue*Decimal(100) if revenue>0 else None;min_profit=config.get('minimum_contribution_profit');min_margin=config.get('minimum_contribution_margin_percent')
 if min_profit is not None and profit<money(min_profit):violations.append(f"Contribution profit is below configured minimum ₹{money(min_profit)}.")
 if min_margin is not None and margin is not None and margin<money(min_margin):violations.append(f"Contribution margin is below configured minimum {money(min_margin)}%.")
 return {'items':lines,'item_revenue':str(money(revenue)),'ingredient_costs':str(money(ingredients)),'delivery_cost':str(delivery),'platform_fee':str(platform),'other_costs':str(other),'known_costs_total':str(money(costs)),'total_estimated_cost':str(money(costs)) if complete else None,'contribution_profit':str(money(profit)) if complete else None,'contribution_margin_percent':str(margin.quantize(Decimal('0.01'))) if complete and margin is not None else None,'costs_complete':complete,'warnings':warnings,'violations':violations,'status':'incomplete_costs' if not complete else ('blocked' if violations else 'approved'),'policy':{'minimum_contribution_profit':None if min_profit is None else str(money(min_profit)),'minimum_contribution_margin_percent':None if min_margin is None else str(money(min_margin))}}
