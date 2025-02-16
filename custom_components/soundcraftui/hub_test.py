from hub import Hub
import asyncio
import logging

async def main():
    hub = Hub(None, "192.168.15.110")
    cn = await hub.test_connection()
    print(cn)

   
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    asyncio.run(main())