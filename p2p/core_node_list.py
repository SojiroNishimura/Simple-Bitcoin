import threading


class CoreNodeList:
    def __init__(self):
        self.lock = threading.Lock()
        self.list = set()

    def add(self, peer):
        with self.lock:
            print('Adding peer: ', peer)
            self.list.add((peer))
            print('Current Core List: ', self.list)

    def remove(self, peer):
        with self.lock:
            if peer in self.list:
                print('Removing peer: ', peer)
                self.list.remove(peer)
                print('Current Core List: ', self.list)

    def overwrite(self, new_list):
        with self.lock:
            print('core node list will be going to overwrite')
            self.list = new_list
            print('Current Core List: ', self.list)

    def get_list(self):
        return self.list

