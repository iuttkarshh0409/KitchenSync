import re
from .database import MENU
def parse_order(text: str) -> dict:
 n=re.sub(r'[^a-z0-9 ]',' ',text.lower());n=re.sub(r'\s+',' ',n).strip();priority='fast' if re.search(r'\b(fast|urgent|rush|asap)\b',n) else None
 clean=re.sub(r'\b(fast|urgent|rush|asap|please|and)\b',' ',n);clean=re.sub(r'\s+',' ',clean).strip();aliases=sorted([(a.lower(),m) for m in MENU for a in m['aliases']],key=lambda x:len(x[0]),reverse=True);results=[]
 while clean:
  found=None
  for alias,item in aliases:
   x=re.search(r'(?<![a-z])'+re.escape(alias)+r'(?![a-z])',clean)
   if x and (found is None or x.start()<found[0]):found=(x.start(),x.end(),item)
  if found is None:results.append({'validation':'error','error':f"Could not identify '{clean}'. Please choose a dish from the menu."});break
  prefix=clean[:found[0]].strip();nums=re.findall(r'\b(\d+)\b',prefix);qty=int(nums[-1]) if nums else 1;item=found[2]
  if qty>50:results.append({'validation':'error','error':'Quantity must be between 1 and 50.'})
  else:results.append({'validation':'valid','menu_item_id':item['id'],'name':item['name'],'quantity':qty,'brand':item['brand'],'station':item['station'],'duration_minutes':item['duration_minutes'],'priority_note':priority})
  clean=(clean[:found[0]]+' '+clean[found[1]:]).strip();clean=re.sub(r'\b\d+\b',' ',clean);clean=re.sub(r'\s+',' ',clean).strip()
 if not results:results=[{'validation':'error','error':'Enter a recognized dish, for example: 2 veg momo.'}]
 return {'items':results,'priority_note':priority,'valid':all(x['validation']=='valid' for x in results)}
