"""12 short student answers to one prompt, with 4 near-duplicate pairs.
Pairs share the SAME substantive strengths/flaws, reworded. If a grader is
consistent, pair members should get (nearly) the same score."""
import json

QUESTION = "Explain why the water cycle is important for life on Earth. (Target: 8-10 sentences)"

RUBRIC = """Score 0-10:
+3 Mechanism: correctly names evaporation, condensation, precipitation, and collection/runoff
+3 Importance: links the cycle to at least three distinct impacts (freshwater supply, agriculture/food, climate regulation, ecosystems/habitats)
+2 Accuracy: no scientific errors
+2 Communication: organized, complete sentences, on target length
Deductions: -1 per scientific error; cap total at 0..10"""

# Pair A: strong answer (full mechanism, 3 impacts, no errors) ~ score 9-10
A1 = """The water cycle moves water through evaporation, condensation, precipitation, and collection. The sun heats oceans and lakes, turning water into vapor that rises. As it cools, the vapor condenses into clouds. Eventually it falls as rain or snow and collects in rivers, lakes, and underground. This cycle matters because it constantly renews our freshwater supply, which humans and animals need to drink. It also waters crops, so our food supply depends on it. Additionally, by moving heat from the equator toward the poles, the cycle helps regulate Earth's climate. Wetlands and rivers refilled by the cycle provide habitats for countless species. Without this cycle, life as we know it could not continue."""
A2 = """Water constantly circulates through four stages: it evaporates from oceans when heated by the sun, condenses into clouds as it cools, falls back down as precipitation, and collects in rivers and groundwater. This endless loop is essential for several reasons. First, it refreshes the planet's supply of drinkable freshwater. Second, farms rely on rainfall to grow the food we eat. Third, the movement of water vapor redistributes heat around the globe, stabilizing the climate. The cycle also sustains rivers and wetlands where fish, birds, and plants live. In short, every living thing depends on water's continuous journey."""

# Pair B: missing mechanism steps (only evaporation+rain), 2 impacts, one error ("water is created") ~ score 4-5
B1 = """The water cycle is when water goes up into the sky and comes back down as rain. The sun makes water evaporate from the sea, and then new water is created in the clouds and falls down. This is important because people need water to drink. Farmers also need rain for their crops to grow. If there was no water cycle everything would dry up and plants would die. That is why the water cycle is important for life on Earth."""
B2 = """The water cycle means water rises up from oceans because of the sun and later falls again as rain. Inside the clouds, brand new water gets made and then it rains down on us. This matters since humans must drink water every day to survive. It also matters because crops in fields need the rain. Without the cycle the land would become dry and nothing could grow anymore. So the water cycle keeps life going."""

# Pair C: good mechanism, only 1 impact, short/choppy ~ score 5-6
C1 = """Water evaporates from the ocean. It condenses into clouds. Then it precipitates as rain or snow. Finally it collects in rivers and soaks into the ground. This cycle gives us fresh water to drink. It repeats forever."""
C2 = """First the sun evaporates seawater. Next the vapor condenses to form clouds. After that, precipitation brings the water down as rain. Then the water collects in lakes and underground. Because of this, people always have fresh drinking water. The process starts over again and again."""

# Pair D: 3 impacts but garbled mechanism (confuses condensation/evaporation), 1 error ~ score 5-6
D1 = """The water cycle keeps Earth alive. Water condenses out of the ocean into the air, then evaporates inside clouds before raining down. Even though the steps are complicated, the results matter: rain fills the reservoirs that towns drink from, irrigates the wheat and rice that feed billions, and keeps forests and swamps alive for animals. The cycle even moves warmth around the planet. Life needs this loop to survive."""
D2 = """Earth stays alive thanks to the water cycle. From the sea, water condenses into the sky, and inside the clouds it evaporates before falling as rain. The outcomes are what count: reservoirs that supply drinking water get refilled, fields of crops that feed the world get irrigated, and wetlands that shelter wildlife stay wet. The cycle also spreads heat across the globe. Without it, living things would perish."""

# 4 singletons of varied quality
S1 = """Rain comes from clouds and goes to the sea. Water is important because we drink it. The end."""  # ~1-2
S2 = """The water cycle has four steps: evaporation, condensation, precipitation, and collection. The sun drives the whole process by heating surface water. Clouds form when vapor cools at altitude. Rain and snow return the water to land. Rivers carry it back to the sea. This supplies drinking water for people and animals and irrigates farmland. It also shapes weather patterns across the world. Every ecosystem, from deserts to rainforests, is built around how much water the cycle delivers."""  # ~9
S3 = """Water evaporates and then it rains. This helps plants grow and gives animals water. The water cycle also cleans the water naturally as it evaporates, leaving salt behind. People use the rain water in wells. It is a very useful process for the whole planet."""  # ~4-5
S4 = """The cycle of water includes evaporation from oceans, condensation into clouds, precipitation, and runoff that collects in rivers. It matters mainly because it provides freshwater. Also gravity pulls the rain down which creates electricity in dams, and this powers cities. The cycle supports fish habitats too. Overall it is fairly important."""  # ~6-7

essays = {"A1":A1,"A2":A2,"B1":B1,"B2":B2,"C1":C1,"C2":C2,"D1":D1,"D2":D2,"S1":S1,"S2":S2,"S3":S3,"S4":S4}
pairs = [("A1","A2"),("B1","B2"),("C1","C2"),("D1","D2")]
json.dump({"question":QUESTION,"rubric":RUBRIC,"essays":essays,"pairs":pairs}, open("essays.json","w"), indent=2)
print("wrote essays.json:", len(essays), "essays,", len(pairs), "near-duplicate pairs")
