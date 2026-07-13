import json
from collections import namedtuple

MbtiQuestion = namedtuple('MbtiQuestion', ['id', 'axis', 'text'])
q = MbtiQuestion(1, "IE", "안녕하세요")

print(json.dumps({'question': q}))
