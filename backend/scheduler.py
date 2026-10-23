from datetime import datetime,timedelta
DURATIONS={'steamer':10,'wok':3};TARGET_WINDOW=2
def schedule_order(items:list[dict],created_at:datetime,availability:dict|None=None)->dict:
 """Optimize first item per station to the earliest common finish, respecting station availability."""
 availability=availability or {};normalized=[{**i,'duration_minutes':int(i.get('duration_minutes') or DURATIONS[i['station']])} for i in items];stations={s:max(created_at,availability.get(s,created_at)) for s in DURATIONS};first={}
 for item in normalized:first.setdefault(item['station'],item)
 target=max((stations[s]+timedelta(minutes=int(item['duration_minutes'])*int(item.get('quantity',1))) for s,item in first.items()),default=created_at);tasks=[];cursor=dict(stations);seen=set()
 for ix,item in enumerate(normalized):
  s=item['station'];duration=int(item['duration_minutes'])*int(item.get('quantity',1))
  if s not in seen:
   finish=max(target,stations[s]+timedelta(minutes=duration));start=finish-timedelta(minutes=duration)
  else:start=max(cursor[s],target-timedelta(minutes=duration));finish=start+timedelta(minutes=duration)
  cursor[s]=finish;seen.add(s);tasks.append({**item,'planned_start':start,'planned_finish':finish,'task_group':f'task-{ix}'})
 finishes=[t['planned_finish'] for t in tasks];deviation=(max(finishes)-min(finishes)).total_seconds()/60 if finishes else 0
 return {'tasks':tasks,'estimated_minutes':max(((f-created_at).total_seconds()/60 for f in finishes),default=0),'sync_deviation_minutes':deviation,'sync_success':deviation<=TARGET_WINDOW,'target_window_minutes':TARGET_WINDOW}
