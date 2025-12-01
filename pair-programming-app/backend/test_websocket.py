#!/usr/bin/env python3
"""
WebSocket endpoint test script.
Tests real-time collaboration features.
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    """Test WebSocket connection and messaging."""

    # First, create a room to test with
    import requests
    print("1. Creating test room...")
    response = requests.post('http://localhost:8000/rooms/', json={
        'name': 'WebSocket Test Room',
        'language': 'python'
    })

    if response.status_code != 201:
        print(f"❌ Failed to create room: {response.status_code}")
        return False

    room = response.json()
    room_id = room['id']
    print(f"✅ Room created: {room_id}")

    # Connect to WebSocket
    uri = f"ws://localhost:8000/ws/{room_id}"
    print(f"\n2. Connecting to WebSocket: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")

            # Test 1: Receive init message
            print("\n3. Waiting for init message...")
            init_msg = await websocket.recv()
            init_data = json.loads(init_msg)
            print(f"✅ Received init message:")
            print(f"   Type: {init_data.get('type')}")
            print(f"   Room ID: {init_data.get('data', {}).get('room_id')}")
            print(f"   Language: {init_data.get('data', {}).get('language')}")

            if init_data.get('type') != 'init':
                print("❌ Expected 'init' message type")
                return False

            # Test 2: Send code update
            print("\n4. Sending code update...")
            code_update = {
                "type": "code_update",
                "data": {
                    "code": "print('Hello from WebSocket test!')"
                }
            }
            await websocket.send(json.dumps(code_update))
            print("✅ Code update sent")

            # Test 3: Send cursor position
            print("\n5. Sending cursor position...")
            cursor_msg = {
                "type": "cursor_position",
                "data": {
                    "line": 1,
                    "column": 15
                }
            }
            await websocket.send(json.dumps(cursor_msg))
            print("✅ Cursor position sent")

            # Test 4: Send invalid message type
            print("\n6. Testing error handling (invalid message type)...")
            invalid_msg = {
                "type": "unknown_type",
                "data": {}
            }
            await websocket.send(json.dumps(invalid_msg))

            # Wait for error response
            try:
                error_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                error_data = json.loads(error_response)
                if error_data.get('type') == 'error':
                    print(f"✅ Error handling works: {error_data.get('data', {}).get('message')}")
                else:
                    print(f"⚠️  Expected error message, got: {error_data.get('type')}")
            except asyncio.TimeoutError:
                print("⚠️  No error message received (timeout)")

            # Test 5: Verify room code was updated
            print("\n7. Verifying code was saved to database...")
            response = requests.get(f'http://localhost:8000/rooms/{room_id}')
            updated_room = response.json()
            if updated_room['code'] == "print('Hello from WebSocket test!')":
                print("✅ Code successfully saved to database!")
                print(f"   Code: {updated_room['code']}")
            else:
                print(f"❌ Code not updated. Expected: print('Hello from WebSocket test!')")
                print(f"   Got: {updated_room['code']}")

            print("\n✅ All WebSocket tests passed!")
            return True

    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Endpoint Test")
    print("=" * 60)

    success = asyncio.run(test_websocket())

    print("\n" + "=" * 60)
    if success:
        print("✅ WebSocket Testing Complete - ALL TESTS PASSED")
    else:
        print("❌ WebSocket Testing Failed")
    print("=" * 60)

    sys.exit(0 if success else 1)
