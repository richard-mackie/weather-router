import heapq
import datetime
import mercantile

class PriorityQueue:
    '''
    Wrapper for heapq
    '''

    def __init__(self):
        self.heap = []

    def empty(self) -> bool:
        # try to get lowest cost
        try:
            x = self.heap[0]
            return False
        # if there is no lowest cost element the priority queue is empty
        except IndexError:
            return True

    def push(self, x):
        heapq.heappush(self.heap, x)

    def pop(self):
        return heapq.heappop(self.heap)

class Node:
    def __init__(self, lat, lng, time, parent, heading):
        self.id = tile_index = mercantile.tile(lat, lng, zoom=10)
        self.lat = lat
        self.lng = lng
        self.time = datetime.timedelta(seconds=time).seconds
        self.parent = parent
        self.heading = heading


# If a tile is in the queue replace it with the lower time cost