import rpc
import logging
import time

from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)
logger = logging.getLogger('vs2lab.lab2.rpc.runcl')

def callback(result):
    logger.info("Asynchronous append result: {}".format(result.value))
    
cl = rpc.Client(asyncAppend=True)
cl.run()

base_list = rpc.DBList({'foo'})
result_list = cl.append('bar', base_list, callback)

#print("Result: {}".format(result_list.value))

logger.info("Sending append request to server...")
start_time = time.time()

result_list = cl.append('bar', base_list)

# Show that client was waiting
elapsed_time = time.time() - start_time
logger.info(f"Received response after {elapsed_time:.2f} seconds")

#print("Result: {}".format(result_list.value))

cl.stop()
