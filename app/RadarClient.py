import json
import math
import threading
import time
import websocket
from app import config


class RadarClient:
    def __init__(self):
        self.resources = {}
        self.players = {}
        self.fishing_zones = {}
        self.exits = {}
        self.chat_messages = []

        self.my_id = None
        self.my_x = 0.0
        self.my_y = 0.0

        self._lock = threading.Lock()
        self._connected = False
        self._ws = None

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        self._ws = websocket.WebSocketApp(
            config.RADAR_WS_URL,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )
        self._ws.run_forever(reconnect=5)

    def _on_open(self, ws):
        self._connected = True
        print("[Radar] Connected")

    def _on_close(self, ws, code, msg):
        self._connected = False
        print("[Radar] Disconnected, reconnecting...")

    def _on_error(self, ws, error):
        print(f"[Radar] Error: {error}")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get("type") == "batch":
                for msg in data.get("messages", []):
                    self._dispatch(msg)
        except Exception:
            pass

    def _dispatch(self, msg):
        kind = msg.get("code")
        d = msg.get("dictionary", {})
        params = d.get("parameters", {})
        event_code = d.get("code") or d.get("operationCode")

        if kind == "event":
            self._handle_event(event_code, params)
        elif kind == "response":
            self._handle_response(event_code, params)

    def _handle_event(self, code, p):
        with self._lock:
            if code == 1:   # Leave
                eid = p.get("0")
                if eid is not None:
                    self.resources.pop(eid, None)
                    self.players.pop(eid, None)
                    self.fishing_zones.pop(eid, None)
                    self.exits.pop(eid, None)

            elif code == 3:  # Move
                eid = p.get("0")
                x = p.get("4")
                y = p.get("5")
                if eid is not None and x is not None and y is not None:
                    if eid == self.my_id:
                        self.my_x = float(x)
                        self.my_y = float(y)
                    elif eid in self.players:
                        self.players[eid]["x"] = float(x)
                        self.players[eid]["y"] = float(y)

            elif code == 29:  # NewCharacter
                eid = p.get("0")
                if eid is not None:
                    self.players[eid] = {
                        "name": p.get("1", ""),
                        "guild": p.get("8", ""),
                        "faction": p.get("53", 0),
                        "x": 0.0,
                        "y": 0.0,
                    }

            elif code == 38:  # NewSimpleHarvestableObject - batch spawn
                self._parse_batch_harvestables(p)

            elif code == 40:  # NewHarvestableObject - individual spawn
                eid = p.get("0")
                loc = p.get("8")
                if eid is not None and isinstance(loc, list) and len(loc) >= 2:
                    self.resources[eid] = {
                        "type": p.get("5", 0),
                        "tier": p.get("7", 0),
                        "enchant": p.get("11", 0) or 0,
                        "x": float(loc[0]),
                        "y": float(loc[1]),
                    }

            elif code == 46:  # HarvestableChangeState
                eid = p.get("0")
                if eid is not None and p.get("1") is None:
                    self.resources.pop(eid, None)

            elif code == 73:  # ChatMessage
                sender = p.get("2", "")
                text = p.get("0", "")
                if text:
                    self.chat_messages.append({"sender": sender, "text": str(text), "time": time.time()})
                    if len(self.chat_messages) > 50:
                        self.chat_messages.pop(0)

            elif code == 216:  # NewExit
                eid = p.get("0")
                loc = p.get("1")
                if eid is not None and isinstance(loc, list) and len(loc) >= 2:
                    self.exits[eid] = {"x": float(loc[0]), "y": float(loc[1])}

            elif code == 360:  # NewFloatObject (fishing bobber zone)
                eid = p.get("0")
                loc = p.get("1")
                if eid is not None and isinstance(loc, list) and len(loc) >= 2:
                    self.fishing_zones[eid] = {"x": float(loc[0]), "y": float(loc[1])}

            elif code == 361:  # NewFishingZoneObject
                eid = p.get("0")
                loc = p.get("1")
                if eid is not None and isinstance(loc, list) and len(loc) >= 2:
                    self.fishing_zones[eid] = {"x": float(loc[0]), "y": float(loc[1])}

    def _handle_response(self, code, p):
        if code == 2:  # JoinResponse - contains our entity ID
            eid = p.get("0")
            if eid is not None:
                with self._lock:
                    self.my_id = eid
                    self.resources.clear()
                    self.players.clear()
                    self.fishing_zones.clear()
                    self.exits.clear()
                    print(f"[Radar] Zone joined, my_id={eid}")

    def _parse_batch_harvestables(self, p):
        ids = p.get("0", [])
        if isinstance(ids, dict):
            ids = ids.get("data", [])
        types = p.get("1", [])
        if isinstance(types, dict):
            types = types.get("data", [])
        tiers = p.get("2", [])
        if isinstance(tiers, dict):
            tiers = tiers.get("data", [])
        positions = p.get("3", [])

        if not isinstance(ids, list):
            return

        for i, eid in enumerate(ids):
            px = float(positions[i * 2]) if isinstance(positions, list) and i * 2 < len(positions) else 0.0
            py = float(positions[i * 2 + 1]) if isinstance(positions, list) and i * 2 + 1 < len(positions) else 0.0
            self.resources[eid] = {
                "type": types[i] if i < len(types) else 0,
                "tier": tiers[i] if i < len(tiers) else 0,
                "enchant": 0,
                "x": px,
                "y": py,
            }

    def is_connected(self):
        return self._connected

    def get_players_nearby(self, radius=None):
        if radius is None:
            radius = config.PLAYER_DANGER_RADIUS
        with self._lock:
            result = []
            for eid, player in self.players.items():
                if eid == self.my_id:
                    continue
                dx = player["x"] - self.my_x
                dy = player["y"] - self.my_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= radius:
                    result.append({**player, "distance": dist, "id": eid})
            return result

    def get_nearest_resource(self, res_type=None, min_tier=None):
        if min_tier is None:
            min_tier = config.RESOURCE_MIN_TIER
        with self._lock:
            best = None
            best_dist = float("inf")
            for eid, res in self.resources.items():
                if res["tier"] < min_tier:
                    continue
                if res_type and self._type_name(res["type"]) != res_type:
                    continue
                dx = res["x"] - self.my_x
                dy = res["y"] - self.my_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < best_dist:
                    best_dist = dist
                    best = {**res, "id": eid, "distance": dist}
            return best

    def has_resources_nearby(self, radius=80, min_tier=None):
        if min_tier is None:
            min_tier = config.RESOURCE_MIN_TIER
        with self._lock:
            for res in self.resources.values():
                if res["tier"] < min_tier:
                    continue
                dx = res["x"] - self.my_x
                dy = res["y"] - self.my_y
                if math.sqrt(dx * dx + dy * dy) <= radius:
                    return True
            return False

    def get_fishing_zones(self):
        with self._lock:
            return list(self.fishing_zones.values())

    def get_exits(self):
        with self._lock:
            return list(self.exits.values())

    def pop_new_chat_messages(self, since_time):
        with self._lock:
            msgs = [m for m in self.chat_messages if m["time"] > since_time]
            return msgs

    def _type_name(self, type_number):
        if 0 <= type_number <= 5:
            return "Log"
        if 6 <= type_number <= 10:
            return "Rock"
        if 11 <= type_number <= 15:
            return "Fiber"
        if 16 <= type_number <= 22:
            return "Hide"
        if 23 <= type_number <= 27:
            return "Ore"
        return "Unknown"
