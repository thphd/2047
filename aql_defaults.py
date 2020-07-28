from aql import AQLController
aqlc = AQLController('http://127.0.0.1:8529', 'db2047',[
'queue',
])
aql = aqlc.aql
