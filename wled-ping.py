#!/usr/bin/env python3

import asyncio
from datetime import datetime
import wled
import math
import subprocess
import re
import typing as t
from colorist import ColorRGB, BgColorRGB
from time import time, sleep


def ping(host: str) -> t.Generator[None, None, t.Optional[int]]:
    proc = subprocess.run(['ping', '-c', '4', host], capture_output=True, text=True)
    vals = []
    for line in proc.stdout.split("\n"):
        if "Request timeout" in line:
            return None
        if "100% packet loss" in line:
            return None
        elif ms := re.search("time=(\d+).\d+ ms", line):
            vals.append(int(ms.group(1)))
    if not vals:
        return None
    return max(vals)  # TODO: p95?


def ms2rgb(p: None | int, max=1000) -> tuple[int, int, int]:
    """
    >>> ms2rgb(None)
    (255, 0, 0)
    >>> ms2rgb(0)
    (0, 255, 0)
    >>> ms2rgb(10)
    (85, 255, 0)
    >>> ms2rgb(100)
    (170, 255, 0)
    >>> ms2rgb(1000)
    (255, 255, 0)
    >>> ms2rgb(10000)
    (127, 0, 0)
    """
    if p is None:
        return (255, 0, 0)
    if p <= 1:
        return (0, 255, 0)
    if p > max:
        return (127, 0, 0)
    return (
        int(math.log10(p) * (255.0/math.log10(max))),
        255,
        0
    )


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description='WLED Ping')
    parser.add_argument('--host', type=str, default='8.8.8.8')
    parser.add_argument('--max', type=int, default=2000)
    parser.add_argument('--timescale', type=int, default=60)
    parser.add_argument('wled')
    return parser.parse_args()


async def main() -> None:
    """Show example on controlling your WLED device."""
    args = parse_args()

    times = []
    async with wled.WLED(args.wled) as led:
        device = await led.update()
        led_count = device.info.leds.count
        time_per_led = ((args.timescale * 60) / led_count)
        print(f"WLED {device.info.version}, {led_count} LEDs, {time_per_led}s per led")

        # await led.master(on=True, brightness=42)

        last_hour = -1
        while True:
            t1 = time()
            sample = ping(args.host)

            times.insert(0, sample)
            if len(times) > led_count:
                times = times[0:led_count]

            rgbs = [ms2rgb(ms, max=args.max) for ms in times]
            ansi = ColorRGB(*rgbs[0])
            current_hour = datetime.now().hour
            if current_hour != last_hour:
                last_hour = current_hour
                print(f"\n{current_hour:2d}: ", flush=True, end="")
            print(f"{ansi}#{ansi.OFF}", flush=True, end="")

            try:
                await led.segment(0, on=True, brightness=255, individual=rgbs)
            except wled.exceptions.WLEDConnectionError:
                print("!", flush=True, end="")

            t2 = time()
            dur = t2 - t1
            delay = time_per_led - dur
            if delay > 0:
                sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
