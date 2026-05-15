import swarm_web
import threading
import time
import sys

def run():
    swarm_web.main()

t = threading.Thread(target=run, daemon=True)
t.start()
time.sleep(2)  # Give it time to start
