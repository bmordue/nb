nb
==

Possible way to use the script:
```
screen
source env/bin/activate
echo "About to run nb.py in foreground; send mail when done"
python3 src/app.py >> /var/log/projects-nb.log 2>&1
echo "Script finished; send email then exit"
echo "Finished nb.py" | mail -s "Finished nb.py" benmordue@gmail.com
exit
```
