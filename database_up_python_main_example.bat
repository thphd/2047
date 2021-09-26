

start arangodb_loop.bat
start arangodb_killer.bat

start database_dump_repeat.bat

set port=5000
start pymain.bat

set port=5001
start pymain.bat

start start_load_balancer.bat

start echo "empty window"