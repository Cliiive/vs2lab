import splitter
import mapper
import reducer
import threading

def main():

    threads = []
    targets = [splitter.splitter, mapper.main, reducer.main]

    for target in targets:
        t = threading.Thread(target=target, name=target.__name__)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    
if __name__ == "__main__":
    main()