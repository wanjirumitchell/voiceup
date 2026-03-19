with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

total = len(lines)
print(f"Total lines: {total}")

# Find the first if __name__ line (should be around 1262)
target_line = None
for i, line in enumerate(lines):
    if line.strip() == "if __name__ == '__main__':":
        print(f"Found at line {i+1}")
        if target_line is None:
            target_line = i

if target_line and target_line < total - 10:
    # Remove lines target_line and target_line+1
    removed1 = lines.pop(target_line)
    removed2 = lines.pop(target_line)  # now target_line points to next line
    print(f"Removed: {removed1.strip()}")
    print(f"Removed: {removed2.strip()}")
    
    # Add them at the very end
    lines.append('\n')
    lines.append("if __name__ == '__main__':\n")
    lines.append("    app.run(debug=True, host='127.0.0.1', port=8080)\n")
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Done! __main__ moved to end. New total: {len(lines)} lines")
else:
    print("No fix needed or already at end")
