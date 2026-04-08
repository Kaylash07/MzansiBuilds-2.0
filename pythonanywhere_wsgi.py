"""
PythonAnywhere WSGI Configuration.

SETUP INSTRUCTIONS:
1. Sign up at https://www.pythonanywhere.com (free account)
2. Go to "Files" tab → upload your project or clone from GitHub:
      git clone https://github.com/YOUR_USERNAME/MzansiBuilds.git
3. Go to "Web" tab → "Add a new web app"
4. Choose "Manual configuration" → Python 3.10+
5. Set "Source code" to: /home/YOUR_USERNAME/MzansiBuilds
6. Open the WSGI configuration file (link on Web tab) and replace ALL contents with:

      import sys
      import os

      project_home = '/home/YOUR_USERNAME/MzansiBuilds'
      if project_home not in sys.path:
          sys.path.insert(0, project_home)

      os.environ['SECRET_KEY'] = 'your-random-secret-key-here'
      os.environ['JWT_SECRET_KEY'] = 'your-random-jwt-secret-here'

      from run import app as application

7. Go to "Web" tab → "Virtualenv" section:
      mkvirtualenv --python=/usr/bin/python3.10 mzansi-env
      pip install -r /home/YOUR_USERNAME/MzansiBuilds/requirements.txt
8. Set "Static files" on Web tab:
      URL: /static/    Directory: /home/YOUR_USERNAME/MzansiBuilds/static
9. Click "Reload" on the Web tab
10. Visit https://YOUR_USERNAME.pythonanywhere.com

Replace YOUR_USERNAME with your actual PythonAnywhere username everywhere above.
"""
