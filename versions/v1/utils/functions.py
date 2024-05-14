from __future__ import annotations

import datetime
import random
import time
from random import sample
from string import ascii_letters, digits
from typing import Callable, Generic, Literal, TypeVar, Union, overload
from binary_reader import BinaryReader


def random_id(k=8):
    return "".join(sample(ascii_letters + digits, k=k))


T = TypeVar("T", bool, Literal[True], Literal[False])


class _MissingSentinel:
    __slots__ = ()

    def __eq__(self, other) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    def __repr__(self):
        return "..."


class ExponentialBackoff(Generic[T]):
    def __init__(self, base: int = 1, *, integral: T = False):
        self._base: int = base
        self._exp: int = 0
        self._max: int = 10
        self._reset_time: int = base * 2 ** 11
        self._last_invocation: float = time.monotonic()
        rand = random.Random()
        rand.seed()
        self._randfunc: Callable[..., Union[int, float]] = (
            rand.randrange if integral else rand.uniform
        )

    @overload
    def delay(self: ExponentialBackoff[Literal[False]]) -> float:
        ...

    @overload
    def delay(self: ExponentialBackoff[Literal[True]]) -> int:
        ...

    @overload
    def delay(self: ExponentialBackoff[bool]) -> Union[int, float]:
        ...

    def delay(self) -> Union[int, float]:
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation
        if interval > self._reset_time:
            self._exp = 0
        self._exp = min(self._exp + 1, self._max)
        return self._randfunc(0, self._base * 2 ** self._exp)


def compute_timedelta(dt: datetime.datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.astimezone()
    now = datetime.datetime.now(datetime.timezone.utc)
    return max((dt - now).total_seconds(), 0)


def get_key(iterable, obj: dict):
    for z in iterable:
        try:
            for x, y in obj.items():
                if z[x] == y:
                    ...
            return z
        except KeyError:
            ...
    return None


def get_attr(iterable, **kwargs):
    for z in iterable:
        try:
            for x, y in kwargs.items():
                if getattr(z, x) != y:
                    raise ValueError
            return z
        except ValueError:
            ...
    return None


def chunks(lst, n):
    result = []
    for i in range(0, len(lst), n):
        result.append(lst[i : i + n])
    return result


def ReadLeb128(buffer: BinaryReader, pos):
    result = 0
    shift = 0
    while 1:
        buffer.seek(pos)
        b = buffer.read_bytes()
        for i, byte in enumerate(b):
            result |= (byte & 0x7F) << shift
            pos += 1
            if not (byte & 0x80):
                result &= (1 << 32) - 1
                result = int(result)
                return result
            shift += 7
            if shift >= 64:
                raise Exception("Too many bytes when decoding varint.")


def WriteLeb128(value):
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)

    return bytes(result)


def calculate_hash(data):
    hash_value = 0x811C9DC5
    prime = 0x1000193
    length = len(data)
    length_aligned = length & ~3

    for i in range(0, length_aligned, 4):
        chunk = data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24)
        hash_value ^= chunk
        hash_value = (hash_value * prime) & 0xFFFFFFFF

    if length - length_aligned > 0:
        remainder = length - length_aligned
        chunk = 0
        for i in range(remainder):
            chunk |= data[length_aligned + i] << (i * 8)
        hash_value ^= chunk
        hash_value = (hash_value * prime) & 0xFFFFFFFF

    return hash_value


# def calculate_hash(data):
#     hash_value = 0x811C9DC5
#     prime = 0x1000193
#     length = len(data)

#     for i in range(0, length & ~3, 4):
#         chunk = int.from_bytes(data[i : i + 4], byteorder="little", signed=True)
#         hash_value ^= chunk
#         hash_value *= prime

#     remainder = length & 3
#     if remainder > 0:
#         part = int.from_bytes(data[-remainder:], byteorder="little", signed=True)
#         hash_value ^= part
#         hash_value *= prime

#     return hash_value & 0xFFFFFFFF


def fake_calculate_hash(data):
    return 0 & 0xFFFFFFFF
