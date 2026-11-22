import asyncio
import sys

from app.schools import CodeRejected, get_verifier

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    if len(sys.argv) != 3:
        print("usage: python -m tools.try_code CODE professor|admin")
        return
    try:
        staff = await get_verifier("demo_db").redeem(sys.argv[1], sys.argv[2], consume=False)
        print("OK:", staff)
    except CodeRejected:
        print("REJECTED")


asyncio.run(main())