#-*- coding: utf-8 -*-

import multiprocessing
import logging

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

class Reactor(object):

    def __init__(self, tasks, func, num_workers=1):
        self.tasks = multiprocessing.Queue()

        for task in tasks:
            self.tasks.put(task)
        self.tasks_len = len(tasks)
        LOG.debug('put %s task(s) in the queue' % len(tasks))

        self.results = multiprocessing.Queue()
        self.func = func
        self.num_workers = num_workers

    def worker(self):
        while True:
            task = self.tasks.get()
            if task is None:
                return
            else:
                self.results.put(self.func(task))

    def run(self):
        workers = []
        for i in range(self.num_workers):
            workers.append(multiprocessing.Process(target=self.worker))

        for w in workers:
            w.start()

        LOG.debug('started %s worker(s)' % len(workers))

        for i in range(self.num_workers):
            self.tasks.put(None)

        self.tasks.close()
        self.tasks.join_thread()

        results = []
        for i in range(self.tasks_len):
            results.append(self.results.get())
        self.results = results

        for w in workers:
            w.join()

        LOG.debug('all tasks processed, all workers exited, received %s results'
                  % len(self.results))
