"""Condition A: independent per-essay grading (no memory of other essays).
Condition B: all essays in ONE prompt (big-context grading).
Metric: |score difference| within near-duplicate pairs (consistency), per condition.
Repeat A twice to also see run-to-run stability."""
import json, re, subprocess, sys

d = json.load(open("essays.json"))
Q, R, E, PAIRS = d["question"], d["rubric"], d["essays"], d["pairs"]
ORDER = ["S2","B1","C2","A1","S1","D2","B2","S3","A2","C1","S4","D1"]  # interleaved so pairs are far apart

def claude(prompt):
    r = subprocess.run(["claude","-p","--model","claude-sonnet-5"], input=prompt,
                       capture_output=True, text=True, timeout=240)
    return r.stdout

def parse_score(raw):
    m = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', raw)
    return float(m.group(1)) if m else None

def cond_A():
    scores = {}
    for k in ORDER:
        p = (f"Grade this student answer strictly with the rubric.\n\nQUESTION: {Q}\n\nRUBRIC:\n{R}\n\n"
             f"ANSWER:\n{E[k]}\n\nRespond ONLY JSON: {{\"score\": <0-10>, \"reason\": \"...\"}}")
        scores[k] = parse_score(claude(p))
    return scores

def cond_B():
    body = "\n\n".join(f"--- ESSAY {k} ---\n{E[k]}" for k in ORDER)
    p = (f"Grade ALL these student answers strictly and CONSISTENTLY with the rubric.\n\n"
         f"QUESTION: {Q}\n\nRUBRIC:\n{R}\n\n{body}\n\n"
         'Respond ONLY JSON: {"scores": {"<id>": <0-10>, ...}}')
    raw = claude(p)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    return {k: float(v) for k,v in json.loads(m.group(0))["scores"].items()} if m else {}

def pair_gaps(scores):
    return {f"{a}-{b}": abs(scores[a]-scores[b]) if scores.get(a) is not None and scores.get(b) is not None else None
            for a,b in PAIRS}

mode = sys.argv[1]
if mode == "A":
    s = cond_A()
else:
    s = cond_B()
print(json.dumps({"mode":mode,"scores":s,"pair_gaps":pair_gaps(s)}, indent=2))
