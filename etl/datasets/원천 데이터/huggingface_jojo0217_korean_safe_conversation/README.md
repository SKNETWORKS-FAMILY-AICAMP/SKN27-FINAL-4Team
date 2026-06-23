---
license: apache-2.0
task_categories:
- text-generation
language:
- ko
---
# 개요
성균관대 - VAIV COMPANY 산학협력을 위해 구축한 일상대화 데이터입니다.   

자연스럽고 윤리적인 챗봇 구축을 위한 데이터셋 입니다.   

고품질을 위해 대부분의 과정에서 사람이 직접 검수하였으며   
생성 번역 등의 과정에서는 GPT3.5-turbo, GPT4를 사용하였습니다.   

일상대화에 중점을 두면서   
혐오표현, 편향적인 대답을 지양하면서 일상대화를 하는 것에 중점을 두었습니다.   

# 데이터 구축 과정   
![score](./img/data_table.png)    

# 데이터 구성   
|데이터 종류|개수|비고|url|
|:---|---:|---:|---:|
|일상대화 데이터셋|2063|국립국어원 모두의 말뭉치|https://corpus.korean.go.kr/request/reausetMain.do?lang=ko|
|감성대화|1020|AIHub 감성대화 데이터|https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&aihubDataSe=realm&dataSetSn=86|
|혐오표현|1126|AIHub 윤리 검증 데이터|https://www.aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&aihubDataSe=realm&dataSetSn=558|
|Evol-inst|476|Evol-inst 방식으로 직접 생성||
|KoAlpaca v1.1|19955|데이터 유사도 검사, 노이즈 제거 등 수정|KoAlpaca/KoAlpaca_v1.1.jsonl at main · Beomi/KoAlpaca (github.com)|
|Yitingxie|1300|rlhf 목적 챗봇 대화 데이터 번역하여 사용|https://huggingface.co/datasets/yitingxie/rlhf-reward-datasets?row=97|
|네이버 SQuARe|1039|네이버 편향성 데이터|https://github.com/naver-ai/korean-safety-benchmarks|
|총합|26979|||

./raw/폴더에 각각 파일이 담겨있습니다.

# contributor   
---   
[JoJo0217](https://github.com/JoJo0217)   
[hap](https://github.com/chohabin)   
[moseoridev](https://github.com/moseoridev)   
[jangjunewoo](https://github.com/jangjunewoo)   
[Y8N](https://github.com/yeyoon4)   