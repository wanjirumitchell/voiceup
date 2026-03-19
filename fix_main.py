with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all lines with if __name__
main_lines = [i for i, l in enumerate(lines) if "__name__ == '__main__'" in l]
print(f"Found __main__ at lines: {[l+1 for l in main_lines]}")

if len(main_lines) >= 1:
    # Remove the first one (around line 1261) and its app.run line
    first = main_lines[0]
    # Remove 2 lines: the if __name__ line and the app.run line
    del lines[first:first+2]
    print(f"Removed block at line {first+1}")

# Write back
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Verify
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

count = content.count("if __name__ == '__main__':")
print(f"Remaining __main__ blocks: {count}")
print("Done! Now run: python app.py")
