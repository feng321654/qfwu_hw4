import json
import random
with open('raw_data/filter_data.json') as f:
    raw_data_list=json.load(f)
with open('raw_data/agent_query.txt') as f:
    agent_queries=f.readlines()
new_data_list=[]
for data in raw_data_list:
    agent_query=random.choice(agent_queries)+f"\n\n{data['buggy_code']}"
    edit_query="代码问题："+data['category']+" "+data['subtype']+f"\n\n{data['buggy_code']}"
    obj1=data.copy()
    obj2=data.copy()
    obj1['query']=agent_query
    obj1['label']='agent'
    obj2['query']=edit_query
    obj2['label']='edit'
    new_data_list.append(obj1)
    new_data_list.append(obj2)
with open('processed_data/query.json','w') as f:
    json.dump(new_data_list,f,ensure_ascii=False,indent=2)