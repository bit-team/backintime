# How to set up a local `openssh-server` to enable ssh unit tests

# Motivation

`ssh`-based unit tests are skipped in `make test` when no local ssh server
is configured and running.

In order to execute also run all ssh unit tests in the `common` folder
via `make test` the `openssh` server must be **installed on your local machine**
and a public/private key must be set up for password-less connections.

This document describes the required steps.

# How the unit tests access the ssh server

`ssh`-based unit tests use the [`common/test/generic.py`](https://github.com/bit-team/backintime/blob/f801b14a98f9a442008a5f514eec98e1b2d7e29a/common/test/generic.py)
to check and establish a ssh connection to the ssh server via this code:

https://github.com/bit-team/backintime/blob/f801b14a98f9a442008a5f514eec98e1b2d7e29a/common/test/generic.py#L43-L72

The code implements the following logic:

1. Check if a `sshd` process is running on the local machine
2. Check if a private key file `~/.ssh/id_rsa` exists
3. Check if the file `~/.ssh/authorized_keys` exists
4. Check if the private key from `id_rsa` is contained in `authorized_keys`
5. Check that the ssh port 22 at localhost is available

If all checks succeed the global variable `LOCAL_SSH` is set to `True`
(and this variable us used then to skip ssh-based unit tests).


# Installation

This installation is based on Ubuntu 20.04.
If you are using another distro please consult the documentation
of your distro when following this installation guide for
required changes.


1. Open a terminal

1. Install openssh-server

   ```commandline
   sudo apt update
   sudo apt install openssh-server
   ```
   
1. Edit the config file to make these changes

   ```commandline
   sudo nano /etc/ssh/sshd_config
   ```
   
   Disable root login by changing this property to:

   ```
   PermitRootLogin no
   ```
   
1. Restart the `sshd`

   ```commandline
   sudo systemctl restart sshd
   ```

1. Authorize sshd logins with a public/private key pair

   Check if you already have a key pair:

   ```
   ls -l ~/.ssh/id_rsa
   ```
   
   If no `id_rsa` file exists create a new public/private key:

   ```commandline
   ssh-keygen -t rsa -b 4096  # saves in ~/.ssh/id_rsa and id_rsa.pub by default
   # Enter and a remember a passphrase to protect your private key!
   ```

   Now copy the public key to the ssh server's `autorized_keys` file:

   ```commandline
   ssh-copy-id -i ~/.ssh/id_rsa.pub username@localhost
   ```

1. Run the BiT unit tests to check if ssh tests do work now

   ```commandline
   cd common
   make test
   ```
   
   You shouldn't see skipped ssh tests now (indicated with an "s" instead of a dot).

# Optionally configure your local firewall to restrict ssh access

**_WARNING_: Do (re)configure and enable your firewall only if you are sure
you know exactly what you are doing. Otherwise you can lock your computer
from any network and internet access and as worst-case even the IP-based
communication to your daemon processes!**

If you have installed a firewall like `ufw` you can check the current settings with

```commandline
$ sudo ufw status verbose
Status: inactive

# Activate the firewall (if shown as "inactive")
$ sudo ufw enable
Firewall is active and enabled on system startup
```

To restrict logins on your `openssh` server to addresses from your local network
you first have to find out your IP address and add the restricted
IP address range to the allowed connections:

```commandline
# show IP address of your computer
ip addr show

# Allow the IP range of your local network (of the correct network adapter)
sudo ufw allow from 192.168.178.12/24 to any port 22

# Check the firewall status
$ sudo ufw status verbose
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere                  
22                         ALLOW IN    192.168.178.0/24          
22/tcp (v6)                ALLOW IN    Anywhere (v6)  

# Disallow ssh access to port 22 for everyone else now...
# Show active firewall rules:
$ sudo ufw status numbered
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere                  
[ 2] 22                         ALLOW IN    192.168.178.0/24          
[ 3] 22/tcp (v6)                ALLOW IN    Anywhere (v6)

# Delete the rule which allows Port 22 access for everyone "from anywhere" (here: Rule #1)
sudo ufw delete 1

# Show remaining rules to determine IP6 rule to be deleted too
$ sudo ufw status numbered
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22                         ALLOW IN    192.168.178.0/24          
[ 2] 22/tcp (v6)                ALLOW IN    Anywhere (v6)

# Delete rule #2 which allows port 22 access (IPv6) from anywhere:
sudo ufw delete 2

# Now check if the remaining rule(s) are plausible:
$ sudo ufw status verbose
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22                         ALLOW IN    192.168.178.0/24  
```

Finally run the unit tests again to make sure the firewall is working correctly
(= not blocking ssh traffic to localhost):

   ```commandline
   cd common
   make test
   ```

# FAQ

## How can I temporarily disable the ssh unit tests since they consume too much time

Just kill the sshd process (works until you restart your computer):

```commandline
# Find the process nubmer of the sshd daemon
$ ps aux | grep -i sshd
root      202345  0.0  0.0  12184  7076 ?        Ss   23:25   0:00 sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups

# Kill the daemon ;-)
sudo kill 202345
```


## How can I permanently enable or disable the ssh server (sshd)?

To disable the `sshd` even when you reboot use:

```commandline
sudo systemctl disable sshd.service
# Requires a restart or killing the sshd process to become effective
```


To enable the `sshd` when booting use:

```
# no typo, the service is named without a "d" !!!
# See also: https://askubuntu.com/questions/978852/enabling-and-disabling-sshd-at-boot-via-systemd
sudo systemctl enable ssh.service
# Restart sshd now to avoid a reboot
sudo systemctl restart sshd
```


## How can I find out if my ssh server (sshd) is running?

```commandline
sudo systemctl status sshd
```