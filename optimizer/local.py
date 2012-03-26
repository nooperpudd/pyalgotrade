# PyAlgoTrade
# 
# Copyright 2011 Gabriel Martin Becedillas Ruiz
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

import multiprocessing
import logging
import socket
import random
from pyalgotrade import optimizer
from pyalgotrade.optimizer import server
from pyalgotrade.optimizer import worker

def server_process(barFeed, strategyParameters, port):
	s = server.Server("localhost", port, True)
	s.serve(barFeed, strategyParameters)

def worker_process(strategyClass, port):
	class Worker(worker.Worker):
		def runStrategy(self, barFeed, *parameters):
			strat = strategyClass(barFeed, *parameters)
			strat.run()
			return strat.getResult()

	# Create a worker and run it.
	w = Worker("localhost", port)
	w.setLogger(optimizer.get_logger("worker", logging.ERROR))
	w.run()

def find_port():
	while True:
		ret = random.randint(1025, 65536)
		try:
			s = socket.socket()
			s.bind(("localhost", ret))
			return ret
		except socket.error:
			pass

def run(strategyClass, barFeed, strategyParameters, workerCount):
	"""Executes many instances of a strategy in parallel and finds the parameters that yield the best results.

	:param strategyClass: The strategy class. Must have a *getResult* method that returns the strategy result.
	:param barFeed: The bar feed to use to backtest the strategy.
	:type barFeed: :class:`pyalgotrade.barfeed.BarFeed`.
	:param strategyParameters: The set of parameters to use for backtesting. An iterable object where each element is a tuple that holds parameter values.
	:param workerCount: The number of strategies to run in parallel.
	:type workerCount: int.
	"""

	assert(workerCount > 0)

	workers = []
	port = find_port()
	if port == None:
		raise Exception("Failed to find a port to listen")

	# Build and start the server.
	serverProcess = multiprocessing.Process(target=server_process, args=(barFeed, strategyParameters, port))
	serverProcess.start()
	
	# Build the worker processes.
	for i in range(workerCount):
		workers.append(multiprocessing.Process(target=worker_process, args=(strategyClass, port)))

	# Start workers
	for process in workers:
		process.start()

	# Wait workers
	for process in workers:
		process.join()

	# Wait the server to finish.
	serverProcess.join()
