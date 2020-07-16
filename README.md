# ftp-python
FTP Server/Client Implementation in Python 3

### Requirements
- Python 3.6 or higher

### ftp_client.py
```
python3 ftp_client.py [ID@IP (ID:optional (default 'admin')] [PORT:optional (default 2022)]
```

### ftp_server.py
```
python3 ftp_server.py [PORT:optional (default 2022)]
```

### Available client arguments
- cd <rem-dir>
- lcd <loc-dir>
- pwd
- lpwd
- ls [<rem-dir>]
- lls [<loc-dir>]
- get <rem-filepath> [<loc-dir>]
- put <loc-filepath> [<rem_dir>]
- exit

### Authentication
- default ID,PW = (admin, adminpw)

### License
All files implemented by Jinho Ko (jinho.ko@postech.ac.kr)  
Personal use and upgraded commit requests are always welcome.
Distribution or commercial use only available upon approval of the author.
