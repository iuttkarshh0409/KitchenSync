from datetime import datetime
from .database import connect
def summary(from_date:str|None=None,to_date:str|None=None):
 with connect() as db:
  clauses=[];params=[]
  if from_date:clauses.append('date(o.created_at)>=date(?)');params.append(from_date)
  if to_date:clauses.append('date(o.created_at)<=date(?)');params.append(to_date)
  where=' WHERE '+' AND '.join(clauses) if clauses else '';orders=db.execute('SELECT * FROM orders o'+where,params).fetchall();tasks=db.execute('SELECT t.* FROM tasks t JOIN orders o ON o.id=t.order_id'+where,params).fetchall();done=[o for o in orders if o['completed_at']];durations=[(datetime.fromisoformat(o['completed_at'])-datetime.fromisoformat(o['created_at'])).total_seconds()/60 for o in done];variance={s:[] for s in ('steamer','wok')};load={s:0 for s in variance};rush={}
  for t in tasks:
   if t['actual_finish']:
    delta=(datetime.fromisoformat(t['actual_finish'])-datetime.fromisoformat(t['planned_finish'])).total_seconds()/60;variance[t['station']].append(abs(delta));load[t['station']]+=max(0,delta)
  for o in done:
   hour=datetime.fromisoformat(o['created_at']).strftime('%H:00');entry=rush.setdefault(hour,{'count':0,'mins':[]});entry['count']+=1;entry['mins'].append((datetime.fromisoformat(o['completed_at'])-datetime.fromisoformat(o['created_at'])).total_seconds()/60)
  synthetic=sum(o['id'].startswith('DEMO-') for o in orders)
  return {'total_orders':len(orders),'completed_orders':len(done),'average_completion_minutes':round(sum(durations)/len(durations),1) if durations else 0,'average_finish_variance_minutes':{s:round(sum(v)/len(v),1) if v else 0 for s,v in variance.items()},'bottleneck_minutes':load,'sync_success_rate':round(100*sum(bool(o['sync_success']) for o in done)/len(done),1) if done else 0,'rush_hours':[{'hour':h,'orders':v['count'],'average_completion_minutes':round(sum(v['mins'])/len(v['mins']),1)} for h,v in sorted(rush.items())],'data_note':f"{synthetic} synthetic demo orders; {len(orders)-synthetic} recorded orders in this date range."}
