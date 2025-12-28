import mediapipe as mp

print("mediapipe file:", mp.__file__)
print("has solutions:", hasattr(mp, "solutions"))
print("dir(mp):", [k for k in dir(mp) if k.startswith("sol")])
print("hands:", mp.solutions.hands)