PREFIX=/usr
DEST=$(DESTDIR)$(PREFIX)

all:

clean:

install: 
	#install plugin
	install -d $(DEST)/share/backintime/plugins
	install --mode=644 plugins/*.py $(DEST)/share/backintime/plugins
	
	#install copyright file
	install -d $(DEST)/share/doc/backintime-notify
	install --mode=644 ../common/debian_specific/copyright $(DEST)/share/doc/backintime-notify
	
