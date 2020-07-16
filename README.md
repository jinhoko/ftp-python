# ftp-python
FTP Server/Client Implementation in Python 3

TERM PROJECT FOR POSTECH CSED353 SPRING 2020
ALL FILES IMPLEMENTED BY JINHO KO (jinho.ko@postech.ac.kr)
DISTRIBUTION OR COMMERCIAL USE ONLY AVAILABLE UPON APPROVAL OF THE AUTHOR.

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
