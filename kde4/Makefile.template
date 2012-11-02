PREFIX=/usr
DEST=$(DESTDIR)$(PREFIX)

all:

clean:
	rm po/*.mo

install:
	#install python
	install -d $(DEST)/share/backintime/kde4
	install --mode=644 *.py $(DEST)/share/backintime/kde4
	
	#install plugin
	install -d $(DEST)/share/backintime/plugins
	install --mode=644 plugins/*.py $(DEST)/share/backintime/plugins
	
	#install application
	install -d $(DEST)/bin
	install backintime-kde4 $(DEST)/bin
	
	#install copyright file
	install -d $(DEST)/share/doc/backintime-kde4
	install --mode=644 ../common/debian_specific/copyright $(DEST)/share/doc/backintime-kde4
	
	#install .desktop file(s)
	install -d $(DEST)/share/applications/kde4
	install --mode=644 *.desktop $(DEST)/share/applications/kde4
	
	#install docbook
	#install -d $(DEST)/share/doc/kde/HTML/en/backintime/figures
	install -d $(DEST)/share/doc/kde/HTML/en/backintime
	install --mode=644 docbook/en/*.docbook $(DEST)/share/doc/kde/HTML/en/backintime
	#install --mode=644 docbook/en/figures/*.png $(DEST)/share/doc/kde/HTML/en/backintime/figures

	#install man file(s)
	for i in $$(ls -1 man/C/); do case $$i in *.gz|*~) continue;; *) gzip --best -c man/C/$$i > man/C/$${i}.gz;; esac; done
	install -d $(DEST)/share/man/man1
	install --mode=644 man/C/*.gz $(DEST)/share/man/man1
