# 用于从原始数据集中筛选python数据，并剔除较难的数据
import json
with open('raw_data/eval.json') as f:
    raw_datas=json.load(f)
new_datas=[]
for data in raw_datas:
    if data['language']!='python3':
        continue
    elif data['level']=='hard':
        continue
    new_data=data.copy()
    new_data.pop("release_time")
    new_datas.append(new_data)

with open('raw_data/filter_data.json','w') as f:
    json.dump(new_datas,f,indent=2,ensure_ascii=False)