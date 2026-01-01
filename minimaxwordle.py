from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from collections import Counter
import time
import sys
import os

def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

with open(resource_path("words.txt"), "r") as file:
    ALL_WORDS = [line.strip().lower() for line in file if len(line.strip()) == 5]

options = webdriver.ChromeOptions()
options.headless = False
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def sim_feedback(secret, guess):
    out = ["absent"] * 5
    remaining = Counter()
    for i in range(5):
        if guess[i] == secret[i]:
            out[i] = "correct"
        else:
            remaining[secret[i]] += 1
    for i in range(5):
        if out[i] == "absent":
            ch = guess[i]
            if remaining[ch] > 0:
                out[i] = "present"
                remaining[ch] -= 1
    return tuple(out)

def filter_possible(possible, guess, observed_states):
    obs = tuple(observed_states)
    return [w for w in possible if sim_feedback(w, guess) == obs]

def choose_minimax_guess(possible, banned):
    best = None
    best_score = float("inf")
    for g in possible:
        if g in banned:
            continue
        buckets = {}
        for s in possible:
            k = sim_feedback(s, g)
            buckets[k] = buckets.get(k, 0) + 1
        worst = max(buckets.values())
        if worst < best_score:
            best_score = worst
            best = g
    return best

def choose_probe_guess(possible, all_words, banned):
    best = None
    best_score = float("inf")
    for g in all_words:
        if g in banned:
            continue
        buckets = {}
        for s in possible:
            k = sim_feedback(s, g)
            buckets[k] = buckets.get(k, 0) + 1
        worst = max(buckets.values())
        if worst < best_score:
            best_score = worst
            best = g
    return best

def type_guess(word):
    body = driver.find_element(By.TAG_NAME, "body")
    for ch in word:
        body.send_keys(ch)
        time.sleep(0.1)  
    body.send_keys(Keys.ENTER)

def wait_row_states(start, end):
    WebDriverWait(driver, 12).until(
        lambda d: all(
            tile.get_attribute("data-state") in {"correct", "present", "absent"}
            for tile in d.find_elements(By.CSS_SELECTOR, "div[data-testid='tile']")[start:end]
        )
    )
    tiles = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='tile']")[start:end]
    return [t.get_attribute("data-state") for t in tiles]

def solve():
    possible = ALL_WORDS[:]
    probes_used = 0
    used_guesses = set() 

    start = 0
    end = 5

    for attempt in range(1, 7):
        if attempt == 1:
            guess = "soare"  
        else:
            remaining_attempts = 6 - attempt
            if len(possible) <= 6 and remaining_attempts >= 2 and probes_used < 2:
                guess = choose_probe_guess(possible, ALL_WORDS, used_guesses)
                probes_used += 1
            else:
                guess = choose_minimax_guess(possible, used_guesses)
        if not guess:
            guess = next((w for w in possible if w not in used_guesses), None)
            if not guess:
                return

        used_guesses.add(guess)

        type_guess(guess)
        time.sleep(2)
        states = wait_row_states(start, end)
        if all(s == "correct" for s in states):
            return
        possible = filter_possible(possible, guess, states)
        if guess in possible:
            possible.remove(guess)

        if not possible:
            return

        start += 5
        end += 5
        time.sleep(0.6)

try:
    driver.get("https://www.nytimes.com/games/wordle/index.html")
    try:
        play_button = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='Play']"))
        )
        play_button.click()
    except:
        pass
    try:
        close_button = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='Modal-module_closeIcon']"))
        )
        close_button.click()
    except:
        pass
    time.sleep(1)
    solve()
finally:
    input("\nPress Enter to quit...")
    driver.quit()
