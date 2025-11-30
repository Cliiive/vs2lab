import rpc
import logging
import time

from context import lab_logging


def callback(result):
    rpc.logger.info("Asynchronous append result: {}".format(result.value))
    
cl = rpc.Client(asyncAppend=True)
cl.run()

base_list = rpc.DBList({'foo'})
try:
    result_list = cl.append('bar', base_list, callback)

    rpc.logger.info("Sending append request to server...")
    start_time = time.time()

    for i in range(20):
        rpc.logger.info("Doing other work while waiting for server response...")
        time.sleep(0.5)

    # Show that client was waiting
    elapsed_time = time.time() - start_time
    rpc.logger.info(f"Received response after {elapsed_time:.2f} seconds")
except Exception as e:
    rpc.logger.warning(e)

cl.stop()
