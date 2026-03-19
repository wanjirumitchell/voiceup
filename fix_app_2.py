with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
i = 0
removed = False
while i < len(lines):
    # Remove the FIRST if __name__ block (around line 887) but not the last one
    if (not removed and 
        lines[i].strip() == "if __name__ == '__main__':" and
        i < 900):
        # Skip this line and the next (app.run line)
        i += 2
        removed = True
        print(f"Removed duplicate __main__ block at line {i}")
        continue
    out.append(lines[i])
    i += 1

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(out)

print("Done! app.py fixed successfully.")
