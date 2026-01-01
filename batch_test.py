import sys
import os
from tqdm import tqdm

def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)
with open(resource_path("words.txt"), "r") as file:
    wordlist = [line.strip().lower() for line in file if len(line.strip()) == 5]

def enter(secret, guess):
    progress = ["grey"] * 5
    used = [False] * 5
    for i in range(5):
        if guess[i] == secret[i]:
            progress[i] = "green"
            used[i] = True
    for i in range(5):
        if progress[i] == "grey":
            for j in range(5):
                if not used[j] and guess[i] == secret[j]:
                    progress[i] = "yellow"
                    used[j] = True
                    break
    return tuple(progress)

def filter_words(possible, guess, key):
    return [w for w in possible if enter(w, guess) == key]

def choose_minimax_guess(possible):
    best = None
    best_score = float("inf")
    for g in possible:
        buckets = {}
        for s in possible:
            k = enter(s, g)
            buckets[k] = buckets.get(k, 0) + 1
        worst = max(buckets.values())
        if worst < best_score:
            best_score = worst
            best = g
    return best

def choose_probe_guess(possible, all_words):
    best = None
    best_score = float("inf")
    for g in all_words:
        buckets = {}
        for s in possible:
            k = enter(s, g)
            buckets[k] = buckets.get(k, 0) + 1
        worst = max(buckets.values())
        if worst < best_score:
            best_score = worst
            best = g
    return best

def main(secret, words):
    possible = words[:]
    probes_used = 0
    for attempt in range(1, 7):
        if attempt == 1:
            guess = "soare"
        else:
            remaining_attempts = 6 - attempt
            if (
                len(possible) <= 6
                and remaining_attempts >= 2
                and probes_used < 2
            ):
                guess = choose_probe_guess(possible, words)
                probes_used += 1
            else:
                guess = choose_minimax_guess(possible)
        key = enter(secret, guess)
        if key == ("green",) * 5:
            return True
        possible = filter_words(possible, guess, key)
        if not possible:
            return False
    return False

fails = []
for w in tqdm(wordlist, desc="Batch test"):
    if not main(w, wordlist):
        fails.append(w)
print("Total fails:", len(fails))
print("Fails:", fails)
