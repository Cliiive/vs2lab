#!/usr/bin/env python3
"""
Main runner to start Splitter, Mappers, and Reducers in separate threads.
NOTE: Current mapper/reducer socket topology appears inconsistent:
 - reducer.py expects mappers to BIND at MAPPER_PORT + i and send pickled tuples
 - mapper.py currently CONNECTs to reducers and sends plain strings
This runner uses the existing functions as-is. For clean shutdown, consider
adding DONE sentinel messages in splitter and matching handling in mapper/reducer.
"""

import threading
import time

import splitter
import mapper
import reducer


def start_splitter():
    splitter.splitter()


def start_mappers():
    # mapper.main() starts all mapper threads internally
    mapper.main()


def start_reducers():
    reducer.main()


def main():
    t_splitter = threading.Thread(target=start_splitter, name="SplitterThread")
    t_mappers = threading.Thread(target=start_mappers, name="MappersThread")
    t_reducers = threading.Thread(target=start_reducers, name="ReducersThread")

    # Start reducers first so they are ready for incoming mapper data
    t_reducers.start()
    time.sleep(0.5)
    # Start mappers next
    t_mappers.start()
    time.sleep(0.5)
    # Finally start splitter (data source)
    t_splitter.start()

    # Wait for splitter to finish
    t_splitter.join()
    # Wait for mappers (may block if no DONE sentinel; adjust logic as needed)
    t_mappers.join()
    # Wait for reducers
    t_reducers.join()

    print("[MAIN] All components finished (or joined).")


if __name__ == "__main__":
    main()
