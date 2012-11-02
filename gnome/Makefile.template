PREFIX=/usr
DEST=$(DESTDIR)$(PREFIX)

all:

clean:

install: 
	#install python
	install -d $(DEST)/share/backintime/gnome
	install --mode=644 *.py $(DEST)/share/backintime/gnome
	install --mode=644 *.glade $(DEST)/share/backintime/gnome
	
	#install plugin
	install -d $(DEST)/share/backintime/plugins
	install --mode=644 plugins/*.py $(DEST)/share/backintime/plugins
	
	#install copyright file
	install -d $(DEST)/share/doc/backintime-gnome
	install --mode=644 ../common/debian_specific/copyright $(DEST)/share/doc/backintime-gnome
	
	#install man file(s)
	for i in $$(ls -1 man/C/); do case $$i in *.gz|*~) continue;; *) gzip --best -c man/C/$$i > man/C/$${i}.gz;; esac; done
	install -d $(DEST)/share/man/man1
	install --mode=644 man/C/*.gz $(DEST)/share/man/man1
	
	#install application
	install -d $(DEST)/bin
	install backintime-gnome $(DEST)/bin
	
	#install .desktop file(s)
	install -d $(DEST)/share/applications
	install --mode=644 *.desktop $(DEST)/share/applications
	
	#install gnome-help file(s)
	#install -d $(DEST)/share/gnome/help/backintime/C/figures
	install -d $(DEST)/share/gnome/help/backintime/C
	install --mode=644 docbook/C/*.xml $(DEST)/share/gnome/help/backintime/C
	#install --mode=644 docbook/C/figures/*.png $(DEST)/share/gnome/help/backintime/C/figures
	
	install -d $(DEST)/share/omf/backintime
	install --mode=644 docbook/C/*.omf $(DEST)/share/omf/backintime

