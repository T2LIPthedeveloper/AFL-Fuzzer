"""
Havoc / stacked mutation stage for greybox API fuzzing.

Applies randomized stacks of low-level mutators (bit/byte flips, arithmetic,
dictionary inserts, splicing) similar to AFL's havoc stage, but operates on
JSON-compatible Python objects used by the Django harness.
"""

from __future__ import annotations

import copy
import logging
import random
import string
from typing import Any, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger("HavocStage")

INTERESTING_8 = [-128, -1, 0, 1, 16, 32, 64, 100, 127]
INTERESTING_16 = [-32768, -129, 128, 255, 256, 512, 1000, 32767, 65535]
INTERESTING_32 = [-2147483648, -100000, 100000, 2147483647, 0xFFFFFFFF]


def _rand_string(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


class HavocStage:
    """Stacked random mutations over structured payloads."""

    def __init__(
        self,
        mutation_engine: Optional[Any] = None,
        dictionary_tokens: Optional[Sequence[str]] = None,
        max_stack: int = 16,
    ):
        self.mutation_engine = mutation_engine
        self.dictionary_tokens = list(dictionary_tokens or [])
        if mutation_engine is not None and not self.dictionary_tokens:
            self.dictionary_tokens = list(getattr(mutation_engine, "dictionary_tokens", []) or [])
        self.max_stack = max_stack
        self.stats: Dict[str, int] = {}

    def _hit(self, name: str) -> None:
        self.stats[name] = self.stats.get(name, 0) + 1

    def _choose_stack_depth(self, energy: int) -> int:
        # Higher energy -> deeper havoc stacks (AFL-like)
        base = max(1, min(self.max_stack, energy // 2 or 1))
        return random.randint(1, base)

    def _mutate_string(self, value: str) -> str:
        if not value:
            value = _rand_string(4)
        op = random.choice(
            ["flip", "insert", "delete", "interesting", "dict", "case", "chunk"]
        )
        self._hit(f"str:{op}")
        chars = list(value)
        if op == "flip" and chars:
            i = random.randrange(len(chars))
            chars[i] = chr(ord(chars[i]) ^ (1 << random.randint(0, 6)))
            return "".join(chars)
        if op == "insert":
            i = random.randint(0, len(chars))
            chars.insert(i, random.choice(string.printable))
            return "".join(chars)
        if op == "delete" and len(chars) > 1:
            del chars[random.randrange(len(chars))]
            return "".join(chars)
        if op == "interesting":
            return random.choice(
                ["", "A" * 256, "../" * 8, "%s%s%s%s", "'\"<>", "\x00\x01\x02"]
            )
        if op == "dict" and self.dictionary_tokens:
            token = random.choice(self.dictionary_tokens)
            i = random.randint(0, len(value))
            return value[:i] + token + value[i:]
        if op == "case":
            return "".join(c.upper() if random.random() < 0.5 else c.lower() for c in value)
        # chunk duplicate / shuffle
        if len(value) >= 4:
            cut = len(value) // 2
            return value[cut:] + value[:cut]
        return value + _rand_string(2)

    def _mutate_int(self, value: int) -> int:
        op = random.choice(["interesting8", "interesting16", "arith", "xor", "swap"])
        self._hit(f"int:{op}")
        if op == "interesting8":
            return random.choice(INTERESTING_8)
        if op == "interesting16":
            return random.choice(INTERESTING_16)
        if op == "arith":
            return value + random.choice([-1000, -35, -1, 1, 35, 1000])
        if op == "xor":
            return value ^ (1 << random.randint(0, 31))
        return random.choice(INTERESTING_32)

    def _mutate_list(self, value: List[Any]) -> List[Any]:
        result = copy.deepcopy(value)
        op = random.choice(["append", "remove", "dup", "mutate_item", "clear"])
        self._hit(f"list:{op}")
        if op == "append":
            result.append(random.choice([_rand_string(4), random.randint(-10, 10), {}, []]))
        elif op == "remove" and result:
            result.pop(random.randrange(len(result)))
        elif op == "dup" and result:
            result.append(copy.deepcopy(random.choice(result)))
        elif op == "mutate_item" and result:
            idx = random.randrange(len(result))
            result[idx] = self._mutate_value(result[idx])
        elif op == "clear":
            result = []
        return result

    def _mutate_dict(self, value: Dict[str, Any]) -> Dict[str, Any]:
        result = copy.deepcopy(value)
        op = random.choice(["add", "remove", "mutate", "rename", "engine"])
        self._hit(f"dict:{op}")
        if op == "add":
            result[_rand_string(5)] = random.choice(
                [_rand_string(6), random.randint(-50, 50), None, True, []]
            )
        elif op == "remove" and result:
            result.pop(random.choice(list(result.keys())), None)
        elif op == "mutate" and result:
            key = random.choice(list(result.keys()))
            result[key] = self._mutate_value(result[key])
        elif op == "rename" and result:
            key = random.choice(list(result.keys()))
            result[_rand_string(5)] = result.pop(key)
        elif op == "engine" and self.mutation_engine is not None:
            try:
                result = self.mutation_engine.mutate_payload(result, num_mutations=1)
            except Exception:
                pass
        return result

    def _mutate_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._mutate_string(value)
        if isinstance(value, bool):
            return not value
        if isinstance(value, int):
            return self._mutate_int(value)
        if isinstance(value, float):
            return float(self._mutate_int(int(value)))
        if isinstance(value, list):
            return self._mutate_list(value)
        if isinstance(value, dict):
            return self._mutate_dict(value)
        if value is None:
            return random.choice([0, "", [], {}, "null"])
        return value

    def havoc(self, seed: Any, energy: int = 8, donor: Optional[Any] = None) -> Any:
        """Apply a havoc stack; optionally splice with a donor seed first."""
        current = copy.deepcopy(seed)
        if donor is not None and random.random() < 0.25 and self.mutation_engine is not None:
            try:
                current = self.mutation_engine.splice(current, donor)
                self._hit("splice")
            except Exception:
                pass
        depth = self._choose_stack_depth(energy)
        for _ in range(depth):
            current = self._mutate_value(current)
        return current

    def deterministic_stages(self, seed: Any) -> List[Any]:
        """
        Lightweight deterministic pass over dict string/int fields
        (AFL bitflip / arithmetic inspired).
        """
        if not isinstance(seed, dict) or not seed:
            return [copy.deepcopy(seed)]
        variants: List[Any] = []
        for key, value in list(seed.items()):
            if isinstance(value, str) and value:
                for i, ch in enumerate(value[:16]):
                    mutated = copy.deepcopy(seed)
                    chars = list(value)
                    chars[i] = chr(ord(ch) ^ 0x20)
                    mutated[key] = "".join(chars)
                    variants.append(mutated)
                    self._hit("det:str_xor")
            if isinstance(value, int):
                for delta in (-1, 1, -35, 35):
                    mutated = copy.deepcopy(seed)
                    mutated[key] = value + delta
                    variants.append(mutated)
                    self._hit("det:arith")
                for interesting in INTERESTING_8[:5]:
                    mutated = copy.deepcopy(seed)
                    mutated[key] = interesting
                    variants.append(mutated)
                    self._hit("det:interesting")
        return variants[:64]

    def summary(self) -> Dict[str, int]:
        return dict(sorted(self.stats.items(), key=lambda kv: -kv[1]))
