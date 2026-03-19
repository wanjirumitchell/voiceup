content = open('app.py', 'r', encoding='utf-8').read()
content = content.replace('mysql = MySQL(app)', 'mysql = MySQL(app)\napp.jinja_env.globals.update(enumerate=enumerate)')
open('app.py', 'w', encoding='utf-8').write(content)
print('Done!')
