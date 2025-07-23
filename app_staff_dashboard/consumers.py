import json
from channels.generic.websocket import AsyncWebsocketConsumer

class OrderNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Add the connected staff member to the 'staff_notifications' channel group
        await self.channel_layer.group_add('staff_notifications', self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Remove the connected staff member from the 'staff_notifications' channel group
        await self.channel_layer.group_discard('staff_notifications', self.channel_name)

    async def receive(self, text_data):
        # You can implement additional logic here if needed
        pass

    async def order_notification(self, event):
        # Send the WebSocket message to the staff member
        await self.send(text_data=json.dumps({
            'type': 'order.notification',
            'order_id': event['order_id'],
            'order_number': event['order_number'],
            'table_number': event['table_number'],
            'order_type': event['order_type'],
            'order_item': event['order_item'],
            'order_time': event['order_time'],
            'order_status': event['order_status'],
        }))

    async def ping(self, event):
        print("Received ping message with a staff pong message")
        await self.send(text_data=json.dumps({
            'type': 'pong',
        }))


class KitchenConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'kitchen'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_notification(self, event):
        order_details = event['order_details']
        await self.send(text_data=json.dumps({
            'type': 'order.notification',
            'order_details': order_details,
        }))

    async def accept_order(self, event):
        accepted_item = event['accepted_item']
        order_status = event['order_status']
        await self.send(text_data=json.dumps({
            'type': 'dish.accepted',
            'accepted_item': accepted_item,
            'order_status': order_status,
        }))
    
    async def dish_completed(self, event):
        completed_dish_data = event['completed_dish_data']
        order_status = event['order_status']
        await self.send(text_data=json.dumps({
            'type': 'dish.completed',
            'completed_dish_data': completed_dish_data,
            'order_status': order_status,
        }))

    async def ping(self, event):
        print("Received ping message with a kitchen pong message")
        await self.send(text_data=json.dumps({
            'type': 'pong',
        }))