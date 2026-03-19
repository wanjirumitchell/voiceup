with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

block = "if __name__ == '__main__':\n    app.run(debug=True, host='127.0.0.1', port=8080)"
first = content.find(block)
last  = content.rfind(block)

if first != last:
    content = content[:first] + content[first + len(block):]
    print("Fixed: removed duplicate __main__ block")
else:
    print("No duplicate found")

if 'jinja_env.globals.update(enumerate=enumerate)' not in content:
    content = content.replace('mysql = MySQL(app)', 'mysql = MySQL(app)\napp.jinja_env.globals.update(enumerate=enumerate)')
    print("Fixed: added enumerate")
else:
    print("enumerate already present")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("All done! Run: python app.py")
