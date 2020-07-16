# ftp-python
FTP Server/Client Implementation in Python 3

### Requirements
- Python 3.6 or higher
- Unix-based OS
-	(Externally) Opened port for TCP connection

### ftp_client.py
```
python3 ftp_client.py [ID@IP (ID:optional (default 'admin')] [PORT:optional (default 2022)]
```

### ftp_server.py
```
python3 ftp_server.py [PORT:optional (default 2022)]
```

### Available client arguments
- cd <rem_dir>
- lcd <loc_dir>
- pwd
- lpwd
- ls [<rem_dir>]
- lls [<loc_dir>]
- get <rem_filepath> [<loc_dir>]
- put <loc_filepath> [<rem_dir>]
- exit

### Authentication
- default ID,PW = (admin, adminpw)

### Performance
- Client-side up/down speed is similar with original ftp.
- Server-side multi user transmission speed is similar with original ftp.

### License
All files implemented by Jinho Ko (jinho.ko@postech.ac.kr)  
Personal use and upgraded commit requests are always welcome.  
Distribution or commercial use only available upon approval of the author.
