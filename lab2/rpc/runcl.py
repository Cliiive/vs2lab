import rpc
import logging

from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)

def callback(result):
    print("Asynchronous append result: {}".format(result))
    
cl = rpc.Client(asyncAppend=True)
cl.run()

base_list = rpc.DBList({'foo'})
result_list = cl.append('bar', base_list, callback)

#print("Result: {}".format(result_list.value))

cl.stop()
