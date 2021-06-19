import asyncio
import websockets as ws
import json

class WSHandler:
    def __init__(self, conn: ws.WebSocketServerProtocol, server) -> None:
        self.server = server
        self.connection = conn
    
    async def handle(self) -> None:
        raise NotImplementedError()

    async def send_message(self, event: str, data, metadata = {}):
        await self.connection.send(json.dumps({
            "event": event,
            "data": data,
            "metadata": metadata
        }))


class Computer(WSHandler):

    def __init__(self, conn: ws.WebSocketServerProtocol, server, id) -> None:
        self.id = id
        super().__init__(conn, server)

    async def handle(self):
        while True:
            msg = await self.connection.recv()
            for c in self.server._clients:
                await c.send_message('message', msg, {'computer_id': self.id})



class Client(WSHandler):

    async def handle(self):
        while True:
            msg = await self.connection.recv()

            try:
                parsed_msg = json.loads(msg)
                msg_type = parsed_msg.get("type")
                if msg_type == "list":
                    await self.send_message(
                        "list",
                        list(self.server._computers.keys()))
                else:
                    if (id := parsed_msg.get("computer_id")) in self.server._computers.keys():
                        print(f"{msg_type.capitalize()}: client {self.connection.local_address[0]} -> Computer {id}")

                        await self.server._computers[id].send_message(
                            parsed_msg.get("type"),
                            parsed_msg.get("data"),
                        )
                    else:
                        await self.send_message("error", "Computer unknow")

            except AttributeError as e:
                await self.send_message("error", "Bad Request")




class Server:
    
    _clients = []
    _computers = {}

    async def new_connection(self, websocket: ws.WebSocketServerProtocol, path: str):
        
        print(f"Connection from {websocket.local_address[0]} at {path}")

        if path == "/":

            try:
                client = Client(websocket, self)
                self._clients.append(client)
                await client.handle()
            except Exception as e:
                if not issubclass(e.__class__, ws.ConnectionClosed):
                    print(e.args)

            finally:
                self._clients.remove(client)

        else:
            id = path.removeprefix("/")

            try:
                computer = Computer(websocket, self, id)
                self._computers[id] = computer
                for c in self._clients:
                   await c.send_message("list", list(self._computers.keys()))
                await computer.handle()

            except Exception as e:
                if not issubclass(e.__class__, ws.ConnectionClosed):
                    print(e.args)
                
            finally:
                self._computers.pop(id)
        
        print(f"Connection lost from {websocket.local_address[0]}")


if __name__ == "__main__":

    IP = ('localhost', 3000)

    server = Server()

    start_server = ws.serve(server.new_connection, *IP)
    print(f"Running server at ws://{IP[0]}:{IP[1]}")

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
