import importlib.util, sys
def load(path):
    spec=importlib.util.spec_from_file_location("sol",path); m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m
sol=load(sys.argv[1] if len(sys.argv)>1 else "solution.py")

R=[]  # (name, fn) each returns True/False
def chk(n):
    def d(f): R.append((n,f)); return f
    return d

@chk("slugify basic")
def _(): return sol.slugify("Hello World")=="hello-world"
@chk("slugify trims punctuation")
def _(): return sol.slugify("  Hi, there!! ")=="hi-there"
@chk("slugify collapses repeats")
def _(): return sol.slugify("a---b   c")=="a-b-c"
@chk("slugify empty->empty")
def _(): return sol.slugify("")==""
@chk("slugify unicode strip")
def _(): return sol.slugify("Café Déjà")=="cafe-deja"

@chk("truncate short unchanged")
def _(): return sol.truncate("hello",10)=="hello"
@chk("truncate adds ellipsis")
def _(): return sol.truncate("hello world",8)=="hello..."
@chk("truncate exact length")
def _(): return sol.truncate("hello",5)=="hello"
@chk("truncate word boundary")
def _(): return sol.truncate("hello world",9)=="hello..."

@chk("parse_ints basic")
def _(): return sol.parse_ints("1,2,3")==[1,2,3]
@chk("parse_ints skips blanks")
def _(): return sol.parse_ints("1,,2, ,3")==[1,2,3]
@chk("parse_ints negatives")
def _(): return sol.parse_ints("-1, 2, -3")==[-1,2,-3]
@chk("parse_ints ignore nonint")
def _(): return sol.parse_ints("1,x,2")==[1,2]

@chk("titlecase basic")
def _(): return sol.titlecase("the quick fox")=="The Quick Fox"
@chk("titlecase small words lower")
def _(): return sol.titlecase("war of the worlds")=="War of the Worlds"
@chk("titlecase first word cap")
def _(): return sol.titlecase("of mice")=="Of Mice"

@chk("wordcount basic")
def _(): return sol.wordcount("a b  c")==3
@chk("wordcount empty zero")
def _(): return sol.wordcount("   ")==0

passed=[]; failed=[]
for n,f in R:
    try: (passed if f() else failed).append(n)
    except Exception: failed.append(n)
print(f"PASS {len(passed)}/{len(R)}")
for n in failed: print("  FAIL:",n)
