import mqttools
import asyncio

async def subscriber():
    client = mqttools.Client('192.168.150.81', 1883)

    print("Client object created")
    
    await client.start()
    print("Client started")

    # Subscribe to two topics in parallel.
    await asyncio.gather(
        client.subscribe('/Player1/Piezo1'),
    )

    print('Waiting for messages.')

    while True:
        message = await client.messages.get()

        if message is None:
            print('Broker connection lost!')
            break

        print(f'Topic:   {message.topic}')
        print(f'Message: {message.message}')


asyncio.run(subscriber())