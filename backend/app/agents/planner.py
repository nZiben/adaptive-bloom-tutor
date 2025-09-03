def next_bloom(current: str, score: float, mode: str) -> str:
    levels = ["remember","understand","apply","analyze","evaluate","create"]
    i = max(0, levels.index(current)) if current in levels else 1
    if mode == "exam":
        if score >= 0.8 and i < len(levels)-1: i += 1
        elif score < 0.4 and i > 0: i -= 1
    else:  # diagnostic
        if score >= 0.7 and i < len(levels)-1: i += 1
        elif score < 0.3 and i > 0: i -= 1
    return levels[i]

def next_difficulty(prev: str, score: float) -> str:
    ladder = ["easy","medium","hard"]
    i = ladder.index(prev) if prev in ladder else 1
    if score >= 0.75 and i < 2: i += 1
    elif score < 0.35 and i > 0: i -= 1
    return ladder[i]
