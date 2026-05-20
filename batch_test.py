import sys
import os
import numpy as np
import torch
from tqdm import tqdm


first_guess = "soare"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"

if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    print(f"Using: {torch.cuda.get_device_name(0)}")
else:
    DEVICE = torch.device("cpu")
    print("CUDA not available, falling back to CPU")

def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

with open(resource_path("words.txt"), "r") as file:
    raw = [line.strip().lower() for line in file if len(line.strip()) == 5]

N = len(raw)
word_to_idx = {w: i for i, w in enumerate(raw)}
wordlist_np = np.array([[ord(c) - ord('a') for c in w] for w in raw], dtype=np.int8)
wordlist = torch.tensor(wordlist_np, dtype=torch.int8, device=DEVICE)

def make_table():
    POWERS = torch.tensor([243, 81, 27, 9, 3], dtype=torch.int32, device=DEVICE)
    CHUNK = 512
    table = torch.zeros((N, N), dtype=torch.int16, device=DEVICE)
    for start in tqdm(range(0, N, CHUNK), desc="Building table"):
        end = min(start + CHUNK, N)
        secrets = wordlist[start:end]
        guesses = wordlist
        green  = (secrets[:, None, :] == guesses[None, :, :])
        s_exp  = secrets[:, None, :, None].int()
        g_exp  = guesses[None, :, None, :].int()
        match  = (s_exp == g_exp)
        valid  = match & ~green[:, :, :, None] & ~green[:, :, None, :]
        yellow = valid.any(dim=2) & ~green
        colours = torch.where(green, torch.tensor(2, device=DEVICE),
                  torch.where(yellow, torch.tensor(1, device=DEVICE),
                                      torch.tensor(0, device=DEVICE)))
        table[start:end] = (colours.to(torch.int32) * POWERS).sum(dim=-1).to(torch.int16)
    return table

table = make_table()

POWERS = torch.tensor([243, 81, 27, 9, 3], dtype=torch.int32, device=DEVICE)
WIN_KEY = int((torch.tensor([2,2,2,2,2], dtype=torch.int32, device=DEVICE) * POWERS).sum())
FIRST_GUESS_IDX = word_to_idx[first_guess]

def best_guess(possible_mask, search_mask, used_mask):
    candidate_idx = possible_mask.nonzero(as_tuple=True)[0] 
    search_idx    = (search_mask & ~used_mask).nonzero(as_tuple=True)[0]

    if len(search_idx) == 0:
        fallback = (possible_mask & ~used_mask).nonzero(as_tuple=True)[0]
        return fallback[0].item() if len(fallback) > 0 else candidate_idx[0].item()
    sub = table[candidate_idx][:, search_idx].long()  

    num_cands = len(candidate_idx)
    num_search = len(search_idx)
    bucket_counts = torch.zeros(num_search, 729, dtype=torch.int32, device=DEVICE)
    bucket_counts.scatter_add_(
        1,
        sub.T.int(),                                      
        torch.ones(num_search, num_cands, dtype=torch.int32, device=DEVICE)
    )
    worst = bucket_counts.max(dim=1).values      
    best_local = worst.argmin().item()
    return search_idx[best_local].item()


def solve_all():
    failed = []
    all_mask = torch.ones(N, dtype=torch.bool, device=DEVICE) 
    for secret_idx in tqdm(range(N), desc="Solving"):
        secret_feedback_row = table[secret_idx] 
        possible_mask = torch.ones(N, dtype=torch.bool, device=DEVICE)
        used_mask = torch.zeros(N, dtype=torch.bool, device=DEVICE)
        probes_used = 0
        solved = False

        for attempt in range(1, 7):
            remaining_attempts = 6 - attempt
            num_possible = possible_mask.sum().item()

            if attempt == 1:
                guess_idx = FIRST_GUESS_IDX
            elif num_possible <= 6 and remaining_attempts >= 2 and probes_used < 2:
                guess_idx = best_guess(possible_mask, all_mask, used_mask)
                probes_used += 1
            else:
                guess_idx = best_guess(possible_mask, possible_mask, used_mask)

            used_mask[guess_idx] = True
            observed_key = secret_feedback_row[guess_idx].item()

            if observed_key == WIN_KEY:
                solved = True
                break

            feedback_col = table[:, guess_idx].long()
            possible_mask = possible_mask & (feedback_col == observed_key)
            possible_mask[guess_idx] = False  

            if possible_mask.sum().item() == 0:
                break

        if not solved:
            failed.append(raw[secret_idx])

    return failed

failed = solve_all()
print(f"\nTotal fails: {len(failed)}")
if failed:
    print(f"Failed words: {failed}")
else:
    print("pass")