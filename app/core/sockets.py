from fastapi import WebSocket

# In‑memory store for active student WebSocket connections
# key: student mobile number, value: WebSocket instance
active_connections: dict[str, WebSocket] = {}
