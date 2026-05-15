import threading
from swarm_web import main
t = threading.Thread(target=main)
t.start()
print("Main server started.")
